import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from triage.scenarios import sample_specs  # noqa: E402
from triage.schema import TriageDiagnosis  # noqa: E402
from validate import check  # noqa: E402
from generate import parse_tickets  # noqa: E402


def test_all_sampled_labels_match_schema():
    for s in sample_specs(500, seed=7):
        TriageDiagnosis(**s.label)


def test_sampler_is_deterministic():
    assert [s.label for s in sample_specs(50, 3)] == [s.label for s in sample_specs(50, 3)]


def test_non_fault_is_low_with_no_skills():
    for s in sample_specs(500, seed=2):
        if s.label["intent"] != "fault":
            assert s.label["severity"] == "low" and s.label["required_skills"] == []


def _row(body, **label):
    base = {"error_code": None, "manufacturer": None, "severity": "medium", "intent": "fault",
            "required_skills": ["solar"], "detected_language": "en"}
    base.update(label)
    return {"ticket": {"channel": "email", "subject": "Problem", "body": body}, "label": base}


def test_validator_flags_missing_code_and_brand_leak():
    assert check(_row("Inverter keeps restarting every day.")) == []
    assert any("missing" in e for e in check(_row("Inverter keeps restarting every day.", error_code="HUA-602")))
    assert any("unlabelled brand" in e for e in check(_row("My Huawei inverter keeps restarting.")))
    assert any("unlabelled code" in e for e in check(_row("It shows 602 on the display all day.")))


def test_parse_tickets():
    ok = '```json\n[{"subject":"a","body":"b"},{"subject":"c","body":"d"}]\n```'
    assert len(parse_tickets(ok, 2)) == 2
    assert parse_tickets(ok, 3) is None
    assert parse_tickets("not json", 1) is None


def test_metrics_parse_and_score():
    from triage.metrics import parse_prediction, score, _norm_code
    good = '```json\n{"error_code":"501","manufacturer":"Huawei","severity":"high","intent":"fault","required_skills":["solar"],"detected_language":"en"}\n```'
    d, j, s = parse_prediction(good)
    assert j and s and d["severity"] == "high"
    assert parse_prediction("no json here") == (None, False, False)
    assert parse_prediction('{"severity":"urgent"}')[1:] == (True, False)  # parses, fails schema
    assert _norm_code("Error 501") == _norm_code("501") == "501"
    gold = [d, {**d, "severity": "low", "intent": "billing", "error_code": None, "manufacturer": None, "required_skills": []}]
    m = score(gold, [d, None], [True, False], [True, False])
    assert m["json_valid"] == 0.5 and m["all_fields_exact"] == 0.5
    m2 = score(gold, gold, [True, True], [True, True])
    assert m2["all_fields_exact"] == 1.0 and m2["severity_macro_f1"] == 1.0 and m2["error_code_acc_when_present"] == 1.0
