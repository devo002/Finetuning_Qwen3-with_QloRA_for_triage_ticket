"""Build the real-ticket OOD test set from data/real/tickets_raw.json + data/real/labels.json.

  python scripts/build_real.py   ->  data/processed/real_test.jsonl
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from split import to_chat  # noqa: E402
from triage.schema import TriageDiagnosis  # noqa: E402

tickets = json.loads((ROOT / "data/real/tickets_raw.json").read_text(encoding="utf-8"))
labels = json.loads((ROOT / "data/real/labels.json").read_text(encoding="utf-8"))
assert {t["ticket_id"] for t in tickets} == set(labels), "ticket/label id mismatch"

rows = []
for t in tickets:
    meta_l = labels[t["ticket_id"]]
    label = {k: meta_l[k] for k in ("error_code", "manufacturer", "severity", "intent",
                                   "required_skills", "detected_language")}
    TriageDiagnosis(**label)
    rows.append(to_chat({
        "id": t["ticket_id"],
        "ticket": {"channel": t["channel"], "subject": t["subject"], "body": t["body"]},
        "label": label,
        "meta": {"scenario": "real", "hard": True, "needs_review": meta_l["review"],
                 "note": meta_l.get("note", "")},
    }))
out = ROOT / "data/processed/real_test.jsonl"
out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in sorted(rows, key=lambda r: r["id"])) + "\n",
               encoding="utf-8")
print(f"{len(rows)} real tickets -> {out}; {sum(r['meta']['needs_review'] for r in rows)} flagged for review")
