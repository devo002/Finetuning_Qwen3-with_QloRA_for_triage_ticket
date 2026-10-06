"""Per-request latency of the merged model served by vLLM (one ticket at a time, warm-up excluded).

  python scripts/bench_vllm.py --name qwen-ft-vllm --splits real_test test --limits 25 100

Writes outputs/preds_<name>_<split>.jsonl in the same format as evaluate.py, so report.py scores it
(accuracy AND latency) next to the other models.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from vllm import LLM, SamplingParams

ROOT = Path(__file__).resolve().parent.parent


def read_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=str(ROOT / "outputs/qwen3-4b-triage-merged"))
    ap.add_argument("--name", default="qwen-ft-vllm")
    ap.add_argument("--splits", nargs="+", default=["real_test", "test"])
    ap.add_argument("--limits", nargs="+", type=int, default=[25, 100], help="tickets per split (same order)")
    ap.add_argument("--warmup", type=int, default=5)
    ap.add_argument("--max-model-len", type=int, default=2048)
    a = ap.parse_args()

    llm = LLM(model=a.model, dtype="half", max_model_len=a.max_model_len, gpu_memory_utilization=0.85)
    tok = llm.get_tokenizer()
    params = SamplingParams(temperature=0.0, max_tokens=160)

    def prompt(r: dict) -> str:
        return tok.apply_chat_template(r["messages"][:2], tokenize=False, add_generation_prompt=True)

    first = read_jsonl(ROOT / "data/processed" / f"{a.splits[0]}.jsonl")
    for r in first[:a.warmup]:  # warm-up: CUDA graphs / caches, not timed
        llm.generate([prompt(r)], params, use_tqdm=False)

    out_dir = ROOT / "outputs"
    out_dir.mkdir(exist_ok=True)
    for split, limit in zip(a.splits, a.limits):
        rows = read_jsonl(ROOT / "data/processed" / f"{split}.jsonl")[:limit]
        preds, t_all = [], time.perf_counter()
        for r in rows:
            t0 = time.perf_counter()
            res = llm.generate([prompt(r)], params, use_tqdm=False)[0]
            dt = time.perf_counter() - t0
            preds.append({"id": r["id"], "raw": res.outputs[0].text, "latency_s": dt,
                          "in_tokens": len(res.prompt_token_ids), "out_tokens": len(res.outputs[0].token_ids),
                          "cost_usd": 0.0})
        wall = time.perf_counter() - t_all
        for p in preds:
            p["wall_s_total"] = wall
        path = out_dir / f"preds_{a.name}_{split}.jsonl"
        path.write_text("\n".join(json.dumps(p, ensure_ascii=False) for p in preds) + "\n", encoding="utf-8")
        lat = sorted(p["latency_s"] for p in preds)
        print(f"{split}: n={len(preds)} p50={lat[len(lat)//2]:.2f}s p95={lat[int(.95*(len(lat)-1))]:.2f}s -> {path}")


if __name__ == "__main__":
    main()
