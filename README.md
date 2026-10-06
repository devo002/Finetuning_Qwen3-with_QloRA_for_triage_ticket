# Fine-tuning a small LLM for support-ticket triage: cost and quality vs. Claude

Can a fine-tuned 4B open model replace the Claude call in [Smart Dispatcher](https://github.com/devo002/Smart-dispatcher-Agent)'s triage step?
I fine-tuned **Qwen3-4B-Instruct-2507** (QLoRA) to read a German/English solar and heat-pump support ticket and return validated JSON
(`error_code`, `manufacturer`, `severity`, `intent`, `required_skills`, `detected_language`), then compared it with the production triage call.

## Result

On 25 real tickets the fine-tuned model matches the production call on accuracy, never breaks the JSON schema, and costs about 17x less per ticket.
It is about 1.4x slower on a T4 GPU.

| 25 real tickets | Production call (Claude Sonnet 4.6) | Fine-tuned Qwen3-4B (merged, vLLM, T4) |
|---|---|---|
| **Accuracy (CORE)** | 0.72 (18/25) | **0.76 (19/25)** |
| Severity / intent accuracy | 0.80 / 0.84 | **0.84 / 0.88** |
| High-severity recall | 1.00 | 1.00 |
| Valid schema | 96% | **100%** |
| **Latency p50 / p95** | **2.08 s / 2.43 s** | 2.95 s / 3.50 s |
| **Cost per 1,000 tickets** | $5.11 | **$0.29** |

CORE accuracy = a ticket is correct only when severity, intent, manufacturer and language are all right.

Other runs on the same 25 tickets: Claude with 8 few-shot examples scores 0.80 (1.51 s, $6.15 per 1,000); untuned Qwen scores 0.36 and fails the
schema on 28% of tickets, so fine-tuning is what makes the small model usable.
On 345 synthetic held-out tickets the fine-tuned model scores 0.98 vs 0.84, but those tickets share the training generator, so I treat the real tickets as the fair test.

**When does it pay off?** Renting a GPU at an assumed $0.35/hour costs about $255/month, so the break-even against the production call is
roughly **48,000-50,000 tickets per month**. Below that the API is cheaper. The $0.29 figure assumes the GPU is busy all the time.

## Caveats

- Only 25 real tickets; one ticket is 4 points, and 13 of my labels are judgement calls (`data/real/labels.json`). Differences of one or two tickets are noise.
- Latency is a loss on a T4 (about 16 tokens/s). Plain HuggingFace inference took 8.4 s per ticket, so vLLM was 2.8x faster. Smaller or quantised models and faster GPUs are untested.
- Synthetic gold labels follow my conventions (`src/triage/scenarios.py`), so skills and error-code format are reported separately.
- The baseline calls Claude exactly as `triage_node` does, with the semantic cache and LangSmith bypassed. Qwen cost = GPU time x $0.35/hour; API cost = measured tokens.

## How it was built

1. **Data:** about 3,500 synthetic tickets from Claude Haiku 4.5 (Batch API, about $1.40). Labels are set in code from scenario specs and checked mechanically; 3,455 passed.
   Split 2,765 / 345 / 345, stratified; 62% English, 24% hard cases. Test also uses the 25 real tickets.
2. **Training:** Unsloth + TRL QLoRA (rank 16), 2 epochs on a free Colab T4, loss on the JSON answer only, tracked in Weights & Biases.
3. **Serving:** adapter merged into fp16 weights, served with vLLM.
4. **Evaluation:** `scripts/report.py` scores every model on the same tickets (accuracy, macro-F1, recall on high-severity, schema validity, latency, cost).

## Layout and reproduction

```
src/triage/     schema, scenario generator, metrics     scripts/    data, training, evaluation
notebooks/      Colab: 01 untuned eval, 02 train, 03 merge + vLLM     data/processed/   train / val / test / real_test
outputs/        predictions, error CSVs, RESULTS.md (weights are not committed)
```

```bash
pip install -r requirements.txt            # API keys go in .env (see .env.example)
python scripts/generate.py plan --run full --n 3500 --seed 2   # then submit / collect
python scripts/validate.py --run full && python scripts/split.py --run full && python scripts/build_real.py
python scripts/baseline_dispatcher.py      # needs the Smart Dispatcher repo cloned into ./Mcp
python scripts/evaluate.py --backend claude --model claude-sonnet-4-6 --name claude-fewshot
# GPU steps: Colab notebooks 01 -> 02 -> 03, then:
python scripts/report.py --errors
```

**Not done yet:** FastAPI service and Docker image, a Qwen 1.5B comparison, a quantised latency test.
