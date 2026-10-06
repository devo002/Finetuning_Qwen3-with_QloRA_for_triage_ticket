"""Parsing + scoring of model outputs against gold labels."""
from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Tuple

from sklearn.metrics import f1_score

from .schema import INTENTS, MANUFACTURERS, SEVERITIES, TriageDiagnosis

LANGS = ["de", "en"]
MFR_CLASSES = MANUFACTURERS + ["none"]


def parse_prediction(raw: str) -> Tuple[Optional[dict], bool, bool]:
    """Return (label_dict | None, json_ok, schema_ok). Tolerates code fences and <think> blocks."""
    text = re.sub(r"<think>.*?</think>", "", raw or "", flags=re.S).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None, False, False
    try:
        obj = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None, False, False
    if not isinstance(obj, dict):
        return None, False, False
    try:
        return TriageDiagnosis(**obj).model_dump(), True, True
    except Exception:  # noqa: BLE001
        return None, True, False


_CODE_PREFIX = re.compile(r"^(error|warning|fehler|code|status|state|fehlercode)[\s:#-]*", re.I)


def _norm_code(c: Optional[str]) -> Optional[str]:
    """Case/whitespace-insensitive; ignores a leading word like 'Error ' so format noise is not scored."""
    if not isinstance(c, str) or not c.strip():
        return None
    return _CODE_PREFIX.sub("", c.strip()).strip().lower() or None


def _macro_f1(gold: List[str], pred: List[str], labels: List[str]) -> float:
    # only classes that occur in gold or predictions, so absent classes (e.g. in a 25-ticket set) don't score 0
    present = [l for l in labels if l in set(gold) | set(pred)]
    return float(f1_score(gold, pred, labels=present, average="macro", zero_division=0))


def score(golds: List[dict], preds: List[Optional[dict]], json_ok: List[bool], schema_ok: List[bool]) -> Dict[str, float]:
    """golds: label dicts; preds: parsed dicts or None (invalid). Invalid outputs count as wrong."""
    n = len(golds)
    BAD = "__invalid__"

    def col(field: str, fn=lambda x: x):
        g = [fn(x[field]) for x in golds]
        p = [fn(x[field]) if x else BAD for x in preds]
        return g, p

    out: Dict[str, float] = {"n": n, "json_valid": sum(json_ok) / n, "schema_valid": sum(schema_ok) / n}
    for field, labels in [("severity", SEVERITIES), ("intent", INTENTS), ("detected_language", LANGS)]:
        g, p = col(field)
        out[f"{field}_macro_f1"] = _macro_f1(g, p, labels)
        out[f"{field}_acc"] = sum(a == b for a, b in zip(g, p)) / n
    g, p = col("manufacturer", lambda m: m or "none")
    # safety-critical: how many genuinely urgent tickets were NOT rated high (under-triage)
    hi = [(x, y) for x, y in zip(preds, golds) if y["severity"] == "high"]
    out["high_sev_recall"] = sum(1 for x, y in hi if x and x["severity"] == "high") / max(1, len(hi))
    out["manufacturer_macro_f1"] = _macro_f1(g, p, MFR_CLASSES)

    code_ok = [x is not None and _norm_code(x["error_code"]) == _norm_code(y["error_code"])
               for x, y in zip(preds, golds)]
    out["error_code_acc"] = sum(code_ok) / n
    present = [i for i, y in enumerate(golds) if y["error_code"]]
    out["error_code_acc_when_present"] = sum(code_ok[i] for i in present) / max(1, len(present))

    skills_ok = [x is not None and set(x["required_skills"]) == set(y["required_skills"])
                 for x, y in zip(preds, golds)]
    out["skills_exact"] = sum(skills_ok) / n
    tp = fp = fn = 0
    for x, y in zip(preds, golds):
        gs, ps = set(y["required_skills"]), set(x["required_skills"]) if x else set()
        tp += len(gs & ps); fp += len(ps - gs); fn += len(gs - ps)
    out["skills_micro_f1"] = 2 * tp / max(1, 2 * tp + fp + fn)

    all_ok = []
    for x, y in zip(preds, golds):
        all_ok.append(x is not None and x["severity"] == y["severity"] and x["intent"] == y["intent"]
                      and x["detected_language"] == y["detected_language"]
                      and (x["manufacturer"] or None) == (y["manufacturer"] or None)
                      and _norm_code(x["error_code"]) == _norm_code(y["error_code"])
                      and set(x["required_skills"]) == set(y["required_skills"]))
    out["all_fields_exact"] = sum(all_ok) / n
    # "core" accuracy: ticket counts as correct only if severity, intent, manufacturer and language are all right
    # (the fields where the answer is not a labelling convention)
    core_ok = [x is not None and x["severity"] == y["severity"] and x["intent"] == y["intent"]
               and x["detected_language"] == y["detected_language"]
               and (x["manufacturer"] or None) == (y["manufacturer"] or None) for x, y in zip(preds, golds)]
    out["core_accuracy"] = sum(core_ok) / n
    return out
