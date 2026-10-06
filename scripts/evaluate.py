"""Generate predictions for one model on one or more datasets. Scoring is done by report.py.

Claude baseline (runs anywhere with an API key):
  python scripts/evaluate.py --backend claude --model claude-haiku-4-5 --name claude-haiku --splits test real_test

Local Qwen, base vs fine-tuned (needs a GPU, e.g. Colab T4):
  python scripts/evaluate.py --backend hf --name qwen-base  --splits test real_test
  python scripts/evaluate.py --backend hf --adapter outputs/qwen3-4b-triage-lora --name qwen-ft --splits test real_test

Writes outputs/preds_<name>_<split>.jsonl  (id, raw, latency_s, in_tokens, out_tokens, cost_usd).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

PRICES = {  # USD per 1M tokens (input, output) - first-party API list prices
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-opus-5-5": (4.0, 20.0),
}
DEFAULT_HF_BASE = "unsloth/Qwen3-4B-Instruct-2507-unsloth-bnb-4bit"


def read_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def few_shot_examples(k: int) -> list[dict]:
    """k deterministic train examples, spread over intent/severity, as prior chat turns."""
    train = read_jsonl(ROOT / "data/processed/train.jsonl")
    seen, picked = set(), []
    for r in train:
        key = (r["label"]["intent"], r["label"]["severity"], r["label"]["detected_language"])
        if key not in seen:
            seen.add(key)
            picked.append(r)
        if len(picked) >= k:
            break
    msgs: list[dict] = []
    for r in picked:
        msgs += [r["messages"][1], r["messages"][2]]
    return msgs


# ---------------------------------------------------------------- Claude
def run_claude(rows: list[dict], model: str, shots: int, workers: int) -> list[dict]:
    import anthropic

    sys.path.insert(0, str(ROOT / "scripts"))
    from generate import load_env
    load_env()
    client = anthropic.Anthropic()
    system = rows[0]["messages"][0]["content"]
    shot_msgs = few_shot_examples(shots)
    pin, pout = PRICES[model]
    extra = {}
    if model in ("claude-sonnet-5-5",):  # thinking cannot be disabled on Sonnet 5.5; keep it minimal
        extra = {"thinking": {"type": "between_tools"}, "output_config": {"effort": "low"}}

    def one(r: dict) -> dict:
        t0 = time.perf_counter()
        resp = client.messages.create(model=model, max_tokens=400, system=system,
                                      messages=shot_msgs + [r["messages"][1]], **extra)
        dt = time.perf_counter() - t0
        raw = "".join(b.text for b in resp.content if b.type == "text")
        u = resp.usage
        return {"id": r["id"], "raw": raw, "latency_s": dt, "in_tokens": u.input_tokens,
                "out_tokens": u.output_tokens,
                "cost_usd": (u.input_tokens * pin + u.output_tokens * pout) / 1e6}

    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(one, rows))


# ---------------------------------------------------------------- local HF
def run_hf(rows: list[dict], base: str, adapter: str | None, batch_size: int, max_new_tokens: int) -> list[dict]:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(adapter or base)
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(base, device_map="auto", torch_dtype=torch.float16)
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter)
    model.eval()

    out = []
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        prompts = [tok.apply_chat_template(r["messages"][:2], tokenize=False, add_generation_prompt=True)
                   for r in batch]
        enc = tok(prompts, return_tensors="pt", padding=True).to(model.device)
        torch.cuda.synchronize()
        t0 = time.perf_counter()
        with torch.no_grad():
            gen = model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False,
                                 pad_token_id=tok.pad_token_id)
        torch.cuda.synchronize()
        dt = time.perf_counter() - t0
        for j, r in enumerate(batch):
            new = gen[j, enc["input_ids"].shape[1]:]
            out.append({"id": r["id"], "raw": tok.decode(new, skip_special_tokens=True),
                        "latency_s": dt / len(batch),  # per-ticket share of the batch time
                        "in_tokens": int(enc["attention_mask"][j].sum()),
                        "out_tokens": int((new != tok.pad_token_id).sum()), "cost_usd": 0.0})
        print(f"  {min(i + batch_size, len(rows))}/{len(rows)}", flush=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["claude", "hf"], required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--splits", nargs="+", default=["test", "real_test"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--model", default="claude-haiku-4-5", help="Claude model id")
    ap.add_argument("--shots", type=int, default=8, help="few-shot examples for the Claude baseline")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--base", default=DEFAULT_HF_BASE)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--max-new-tokens", type=int, default=160)
    a = ap.parse_args()

    out_dir = ROOT / "outputs"
    out_dir.mkdir(exist_ok=True)
    for split in a.splits:
        rows = read_jsonl(ROOT / "data/processed" / f"{split}.jsonl")
        if a.limit:
            rows = rows[:a.limit]
        print(f"[{a.name}] {split}: {len(rows)} tickets")
        t0 = time.perf_counter()
        preds = (run_claude(rows, a.model, a.shots, a.workers) if a.backend == "claude"
                 else run_hf(rows, a.base, a.adapter, a.batch_size, a.max_new_tokens))
        wall = time.perf_counter() - t0
        for p in preds:
            p["wall_s_total"] = wall
        path = out_dir / f"preds_{a.name}_{split}.jsonl"
        path.write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in preds) + "\n", encoding="utf-8")
        print(f"  wrote {path}  ({wall:.1f}s, cost ${sum(p['cost_usd'] for p in preds):.4f})")


if __name__ == "__main__":
    main()
