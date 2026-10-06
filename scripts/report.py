"""Score all outputs/preds_*.jsonl and print a markdown comparison table.

  python scripts/report.py [--gpu-hour-usd 0.35] [--out outputs/report.md]

Cost per 1,000 tickets: API models = measured token cost; local models = GPU-hours used * --gpu-hour-usd
(default 0.35 USD/h, a rough rented T4/L4 price - change it to what you actually pay).
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from triage.metrics import parse_prediction, score  # noqa: E402


def read_jsonl(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gpu-hour-usd", type=float, default=0.35)
    ap.add_argument("--out", default=str(ROOT / "outputs/report.md"))
    ap.add_argument("--errors", action="store_true", help="also write outputs/errors_<model>_<split>.csv with every wrong ticket")
    a = ap.parse_args()

    rows_out = []
    for path in sorted((ROOT / "outputs").glob("preds_*.jsonl")):
        stem = path.stem[len("preds_"):]
        split = next(s for s in ("real_test", "test", "val") if stem.endswith("_" + s))
        name = stem[: -len(split) - 1]
        gold_rows = {r["id"]: r for r in read_jsonl(ROOT / "data/processed" / f"{split}.jsonl")}
        preds = read_jsonl(path)
        golds, parsed, jok, sok = [], [], [], []
        for p in preds:
            d, j, s = parse_prediction(p["raw"])
            golds.append(gold_rows[p["id"]]["label"]); parsed.append(d); jok.append(j); sok.append(s)
        m = score(golds, parsed, jok, sok)
        if a.errors:
            import csv
            keys = ["error_code", "manufacturer", "severity", "intent", "required_skills", "detected_language"]
            with open(ROOT / f"outputs/errors_{name}_{split}.csv", "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["id", "ticket"] + [f"gold_{k}" for k in keys] + [f"pred_{k}" for k in keys])
                for p, g, d in zip(preds, golds, parsed):
                    if d is None or any(d[k] != g[k] for k in keys):
                        w.writerow([p["id"], gold_rows[p["id"]]["messages"][1]["content"]]
                                   + [g[k] for k in keys] + [d[k] if d else "INVALID: " + p["raw"][:80] for k in keys])
        lat = [p["latency_s"] for p in preds]
        api_cost = sum(p["cost_usd"] for p in preds)
        cost = api_cost if api_cost > 0 else preds[0]["wall_s_total"] / 3600 * a.gpu_hour_usd
        m.update({"model": name, "split": split, "p50_latency_s": statistics.median(lat),
                  "p95_latency_s": sorted(lat)[int(0.95 * (len(lat) - 1))],
                  "cost_per_1k": cost / len(preds) * 1000})
        rows_out.append(m)

    cols = [("model", "model"), ("split", "split"), ("n", "n"), ("json_valid", "JSON ok"), ("schema_valid", "schema ok"),
            ("core_accuracy", "CORE acc"), ("severity_acc", "sev acc"), ("intent_acc", "intent acc"), ("severity_macro_f1", "sev F1"), ("high_sev_recall", "high-sev recall"), ("intent_macro_f1", "intent F1"), ("manufacturer_macro_f1", "mfr F1"),
            ("detected_language_macro_f1", "lang F1"), ("error_code_acc", "code acc"),
            ("error_code_acc_when_present", "code acc (present)"), ("skills_exact", "skills exact"),
            ("all_fields_exact", "all exact"), ("p50_latency_s", "p50 s"), ("p95_latency_s", "p95 s"),
            ("cost_per_1k", "$/1k")]
    lines = ["| " + " | ".join(c[1] for c in cols) + " |", "|" + "---|" * len(cols)]
    for m in sorted(rows_out, key=lambda m: (m["split"], m["model"])):
        cells = [m[k] if isinstance(m[k], (str, int)) else (f"{m[k]:.3f}" if k != "cost_per_1k" else f"{m[k]:.2f}")
                 for k, _ in cols]
        lines.append("| " + " | ".join(str(c) for c in cells) + " |")
    text = "\n".join(lines)
    Path(a.out).write_text(text + "\n", encoding="utf-8")
    (ROOT / "outputs/report.json").write_text(json.dumps(rows_out, indent=1), encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
