"""Stratified 80/10/10 split + chat formatting + review sample.

  python scripts/split.py --run full

Outputs (data/processed/): train.jsonl, val.jsonl, test.jsonl  (chat format + meta)
                           data/review/review_sample.csv       (rows to check by hand)
Train rows that are near-duplicates of any val/test row are dropped from train.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from triage.schema import TRIAGE_SYSTEM_PROMPT, format_ticket  # noqa: E402

KEYS = ["error_code", "manufacturer", "severity", "intent", "required_skills", "detected_language"]


def shingles(text: str, n: int = 3) -> set:
    w = re.findall(r"\w+", text.lower())
    return {" ".join(w[i:i + n]) for i in range(max(1, len(w) - n + 1))}


def to_chat(r: dict) -> dict:
    t = r["ticket"]
    target = json.dumps({k: r["label"][k] for k in KEYS}, ensure_ascii=False)
    return {
        "id": r["id"],
        "messages": [
            {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
            {"role": "user", "content": format_ticket(t["channel"], t["subject"], t["body"])},
            {"role": "assistant", "content": target},
        ],
        "label": r["label"], "meta": r["meta"],
    }


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="full")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dup-threshold", type=float, default=0.5)
    ap.add_argument("--review-n", type=int, default=150)
    a = ap.parse_args()
    rng = random.Random(a.seed)

    rows = [json.loads(l) for l in (ROOT / "data/generated" / a.run / "clean.jsonl")
            .read_text(encoding="utf-8").splitlines() if l.strip()]

    # stratify on intent / severity / hard / language so every split sees every kind of ticket
    strata: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        strata[(r["label"]["intent"], r["label"]["severity"], r["meta"]["hard"],
                r["label"]["detected_language"])].append(r)
    train, val, test = [], [], []
    for _, grp in sorted(strata.items(), key=lambda kv: str(kv[0])):
        rng.shuffle(grp)
        n = len(grp)
        n_val = n_test = max(1, round(n * 0.1)) if n >= 5 else 0
        test += grp[:n_test]
        val += grp[n_test:n_test + n_val]
        train += grp[n_test + n_val:]

    # near-duplicate guard: drop train rows too similar to any val/test row
    held = [shingles(r["ticket"]["subject"] + " " + r["ticket"]["body"]) for r in val + test]
    kept, dropped = [], 0
    for r in train:
        s = shingles(r["ticket"]["subject"] + " " + r["ticket"]["body"])
        if any(len(s & h) / max(1, len(s | h)) >= a.dup_threshold for h in held):
            dropped += 1
        else:
            kept.append(r)
    train = kept

    out = ROOT / "data/processed"
    for name, part in [("train", train), ("val", val), ("test", test)]:
        rng.shuffle(part)
        write_jsonl(out / f"{name}.jsonl", [to_chat(r) for r in part])

    # review sample: random, but oversample hard cases so label doubts surface
    hard = [r for r in rows if r["meta"]["hard"]]
    easy = [r for r in rows if not r["meta"]["hard"]]
    sample = rng.sample(hard, min(len(hard), a.review_n // 3)) + rng.sample(easy, a.review_n - a.review_n // 3)
    rev = ROOT / "data/review"
    rev.mkdir(parents=True, exist_ok=True)
    with open(rev / "review_sample.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "scenario", "hard", "channel", "subject", "body"] + KEYS + ["label_ok(y/n)", "fix_notes"])
        for r in sample:
            t, l = r["ticket"], r["label"]
            w.writerow([r["id"], r["meta"]["scenario"], r["meta"]["hard"], t["channel"], t["subject"], t["body"]]
                       + [json.dumps(l[k], ensure_ascii=False) if isinstance(l[k], list) else l[k] for k in KEYS]
                       + ["", ""])

    print(f"train {len(train)}  val {len(val)}  test {len(test)}  (dropped {dropped} near-duplicate train rows)")
    for name, part in [("train", train), ("val", val), ("test", test)]:
        c = lambda f: dict(Counter(f(r) for r in part))  # noqa: E731
        print(f"{name}: intent={c(lambda r: r['label']['intent'])} sev={c(lambda r: r['label']['severity'])} "
              f"lang={c(lambda r: r['label']['detected_language'])} hard={sum(r['meta']['hard'] for r in part)}")
    print(f"review sample: {len(sample)} rows -> {rev / 'review_sample.csv'}")


if __name__ == "__main__":
    main()
