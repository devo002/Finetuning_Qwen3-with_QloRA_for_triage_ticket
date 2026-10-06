"""Mechanical quality checks on generated tickets (run before you read them by hand).

  python scripts/validate.py --run pilot

Writes data/generated/<run>/clean.jsonl (passing rows) and rejected.jsonl (with reasons).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from triage.scenarios import FAULTS, UNKNOWN_CODES  # noqa: E402
from triage.schema import MANUFACTURERS, TriageDiagnosis  # noqa: E402

KNOWN_CODES = sorted({c for f in FAULTS for c in f.codes} |
                     {c for u in UNKNOWN_CODES.values() for c in u["codes"]}, key=len, reverse=True)  # type: ignore[union-attr]
BRAND_RE = re.compile(r"\b(?:" + "|".join(MANUFACTURERS) + r")\b", re.I)


def contains_code(text: str, code: str) -> bool:
    return re.search(r"(?<![\w.])" + re.escape(code) + r"(?![\w])", text, re.I) is not None


def shingles(text: str, n: int = 3) -> set:
    w = re.findall(r"\w+", text.lower())
    return {" ".join(w[i:i + n]) for i in range(max(1, len(w) - n + 1))}


def check(row: dict) -> list[str]:
    errs: list[str] = []
    try:
        TriageDiagnosis(**row["label"])
    except Exception as e:  # noqa: BLE001
        return [f"schema: {e}"]
    t, lab = row["ticket"], row["label"]
    text = t["subject"] + "\n" + t["body"]
    if len(t["body"]) < 15:
        errs.append("body too short")
    if lab["error_code"] and not contains_code(text, lab["error_code"]):
        errs.append(f"code {lab['error_code']!r} missing from text")
    if not lab["error_code"]:
        leaked = [c for c in KNOWN_CODES if contains_code(text, c)]
        if leaked:
            errs.append(f"unlabelled code in text: {leaked}")
    found = {m.group(0).lower() for m in BRAND_RE.finditer(text)}
    if lab["manufacturer"] and lab["manufacturer"].lower() not in found:
        errs.append(f"brand {lab['manufacturer']} missing from text")
    if not lab["manufacturer"] and found:
        errs.append(f"unlabelled brand in text: {sorted(found)}")
    if re.search(r"synthetic|as an ai|language model", text, re.I):
        errs.append("meta leakage")
    return errs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="pilot")
    ap.add_argument("--dup-threshold", type=float, default=0.6, help="Jaccard on word trigrams")
    a = ap.parse_args()
    d = ROOT / "data" / "generated" / a.run
    rows = [json.loads(l) for l in (d / "tickets.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

    clean, rejected, sigs = [], [], []
    for r in rows:
        errs = check(r)
        sh = shingles(r["ticket"]["subject"] + " " + r["ticket"]["body"])
        if not errs:
            for other_id, o in sigs:
                if len(sh & o) / max(1, len(sh | o)) >= a.dup_threshold:
                    errs.append(f"near-duplicate of {other_id}")
                    break
        if errs:
            rejected.append({**r, "reasons": errs})
        else:
            clean.append(r)
            sigs.append((r["id"], sh))

    (d / "clean.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in clean) + "\n", encoding="utf-8")
    (d / "rejected.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rejected) + "\n", encoding="utf-8")
    print(f"{len(rows)} rows: {len(clean)} clean, {len(rejected)} rejected")
    reasons = Counter(x.split(":")[0] for r in rejected for x in r["reasons"])
    if reasons:
        print("rejection reasons:", dict(reasons))
    for k in ("intent", "severity", "detected_language"):
        print(f"{k}:", dict(Counter(r["label"][k] for r in clean)))
    print("hard cases:", sum(r["meta"]["hard"] for r in clean))


if __name__ == "__main__":
    main()
