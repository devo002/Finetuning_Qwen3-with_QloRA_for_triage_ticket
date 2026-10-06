# Results (Qwen3-4B fine-tune vs Claude baselines)

Rows:
- dispatcher-prod: exact production Smart Dispatcher triage call (claude-sonnet-4-6, forced tool call, no examples; cache + LangSmith bypassed).
- claude-fewshot: same model, 8 training examples as few-shot, JSON reply.
- qwen-base: Qwen3-4B-Instruct-2507 (4-bit), NO fine-tuning, same system prompt (Colab T4, batch size 8).
- qwen-ft-vllm: adapter merged into fp16 weights, served with vLLM (T4), real_test only (25).
- qwen-ft: same model + QLoRA adapter (2 epochs, 2,765 synthetic tickets), Colab T4, batch size 8.

Test = 345 synthetic held-out tickets. real_test = 25 tickets from the Smart Dispatcher repo (13 labels flagged ambiguous).

| model | split | n | JSON ok | schema ok | CORE acc | sev acc | intent acc | sev F1 | high-sev recall | intent F1 | mfr F1 | lang F1 | code acc | code acc (present) | skills exact | all exact | p50 s | p95 s | $/1k |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-fewshot | real_test | 25 | 1.000 | 1.000 | 0.800 | 0.840 | 0.920 | 0.830 | 1.000 | 0.661 | 1.000 | 1.000 | 0.960 | 0.917 | 0.640 | 0.520 | 1.511 | 2.290 | 6.15 |
| dispatcher-prod | real_test | 25 | 1.000 | 0.960 | 0.720 | 0.800 | 0.840 | 0.813 | 1.000 | 0.582 | 0.957 | 0.980 | 0.960 | 1.000 | 0.520 | 0.480 | 2.078 | 2.425 | 5.11 |
| qwen-base | real_test | 25 | 1.000 | 0.720 | 0.360 | 0.440 | 0.640 | 0.542 | 0.750 | 0.550 | 0.861 | 0.791 | 0.720 | 0.833 | 0.360 | 0.240 | 2.816 | 2.855 | 0.30 |
| qwen-ft | real_test | 25 | 1.000 | 1.000 | 0.720 | 0.800 | 0.880 | 0.776 | 1.000 | 0.588 | 0.952 | 1.000 | 1.000 | 1.000 | 0.800 | 0.640 | 2.561 | 2.876 | 0.32 |
| claude-fewshot | test | 345 | 1.000 | 1.000 | 0.875 | 0.959 | 0.957 | 0.962 | 0.894 | 0.935 | 0.982 | 0.963 | 0.997 | 1.000 | 0.745 | 0.652 | 1.419 | 2.767 | 6.31 |
| dispatcher-prod | test | 345 | 1.000 | 0.980 | 0.841 | 0.928 | 0.954 | 0.943 | 0.846 | 0.957 | 0.971 | 0.948 | 0.954 | 0.954 | 0.612 | 0.510 | 2.133 | 2.960 | 5.29 |
| qwen-base | test | 345 | 1.000 | 0.884 | 0.562 | 0.745 | 0.788 | 0.806 | 0.856 | 0.744 | 0.900 | 0.823 | 0.875 | 0.912 | 0.458 | 0.351 | 3.226 | 3.484 | 0.34 |
| qwen-ft | test | 345 | 1.000 | 1.000 | 0.980 | 0.997 | 0.997 | 0.997 | 1.000 | 0.995 | 1.000 | 0.981 | 1.000 | 1.000 | 0.994 | 0.977 | 3.061 | 3.323 | 0.31 |

Reading guide
- CORE acc = ticket fully correct on severity + intent + manufacturer + language (non-convention fields). Main accuracy number.
- Convention-dependent (my labelling rules vs model judgement): skills exact, code acc, all exact. qwen-ft is trained on my conventions, so its advantage there is not a fair accuracy win.
- Latency: API rows are per-request. qwen-ft / qwen-base rows are batch time / 8 on a T4 (throughput view). qwen-ft-bs1 = one ticket at a time on 100 test tickets = the fair per-request number: p50 8.4 s with plain HuggingFace + 4-bit bitsandbytes (~48 output tokens at ~6 tok/s). That is SLOWER than the API (1.4-2.1 s). qwen-ft-vllm = merged fp16 model on vLLM, T4, one ticket at a time, 25 real tickets, warm-up excluded: p50 2.95 s (~16 tok/s) - 2.8x faster than plain HF, still slower than the API (1.5-2.1 s) on this GPU.
- $/1k for Qwen = GPU time x an assumed $0.35/h (placeholder); for API rows = real token cost.
- With 25 real tickets one ticket = 4 points; 13 of those labels are ambiguous. Treat real_test differences below ~8 points as noise.
- Wrong tickets with gold vs prediction: errors_<model>_<split>.csv. Raw predictions: preds_*.jsonl. Adapter: qwen3-4b-triage-lora/.
