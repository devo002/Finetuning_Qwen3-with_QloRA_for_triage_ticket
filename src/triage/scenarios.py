"""Scenario catalog + sampler.

Gold labels are decided HERE, in code, from the scenario spec. The LLM only writes the
ticket text for a given spec, so labels are correct by construction and can be checked
mechanically (e.g. the error code must appear verbatim in the text).

Error codes / symptoms come from Smart Dispatcher's data/known_issues.md.
Labelling conventions (review these - they are choices, not facts):
  - error_code = the code string exactly as written in the ticket, else null.
  - manufacturer = only if the brand is named in the ticket, else null.
  - any fault described anywhere in the ticket => intent "fault" (even inside a billing mail).
  - non-fault tickets => severity "low", required_skills [].
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

EN_SHARE = 0.62  # share of English tickets (dominant language)
REGIONS = ["Munich", "Hamburg", "Berlin", "Frankfurt", "Stuttgart", "Cologne", "Düsseldorf"]

# (severity, plain-English description of what the customer experiences)
State = Tuple[str, str]


@dataclass
class Fault:
    key: str
    equipment: str                 # generic, brand-free
    manufacturer: Optional[str]    # None => brand is never named
    codes: List[str]               # surface forms; empty => symptom-only scenario
    skills: List[str]
    states: List[State]


FAULTS: List[Fault] = [
    Fault("hua_grid_low", "solar inverter", "Huawei", ["HUA-001", "001"], ["solar"], [
        ("high", "red LED on the inverter and the system produces no power at all, grid connection lost"),
        ("medium", "inverter loses the grid connection several times a day but comes back"),
    ]),
    Fault("hua_dc_insulation", "solar inverter", "Huawei", ["HUA-501", "501"], ["solar"], [
        ("high", "inverter has shut down completely with a yellow LED, no yield since yesterday"),
        ("medium", "a DC insulation warning appears but the inverter still runs for part of the day"),
    ]),
    Fault("hua_grid_high", "solar inverter", "Huawei", ["HUA-602", "602"], ["solar"], [
        ("medium", "output is throttled around noon during peak sun, power drops for hours"),
        ("high", "inverter switches off completely every midday and stays off"),
    ]),
    Fault("sma_selftest", "solar inverter", "SMA", ["SMA-301", "301"], ["solar"], [
        ("medium", "inverter keeps cycling on and off, restarting repeatedly"),
        ("high", "inverter will not start at all, display shows a fault, no solar power"),
    ]),
    Fault("sma_fan", "solar inverter", "SMA", ["SMA-410", "410"], ["solar"], [
        ("medium", "loud grinding or rattling noise from the inverter fan, still producing power"),
    ]),
    Fault("fro_dc", "solar inverter", "Fronius", ["FRO-1010", "1010"], ["solar"], [
        ("medium", "inverter restarts every few hours, production is patchy"),
        ("high", "inverter has stopped and stays dark, no production"),
    ]),
    Fault("goo_battery_comm", "home battery storage", "Goodwe", ["GOO-115", "115"], ["battery"], [
        ("medium", "battery shows offline / communication lost, solar still works but battery does not charge or discharge"),
    ]),
    Fault("vai_low_pressure", "heat pump", "Vaillant", ["F.22", "F22"], ["heatpump", "refrigerant", "brazing"], [
        ("high", "no heating and no hot water at all, display shows a fault"),
        ("medium", "heating works but is weak and takes much longer than before"),
    ]),
    Fault("vie_compressor", "heat pump", "Viessmann", ["A9"], ["heatpump"], [
        ("high", "heat pump will not start on cold mornings, house is cold"),
        ("medium", "heat pump only starts after several attempts, works afterwards"),
    ]),
    # symptom-only scenarios (no brand, no code)
    Fault("bat_lfp_ov", "home battery storage", None, [], ["battery"], [
        ("medium", "battery will not charge above about 90 percent for the last week, no specific error"),
    ]),
    Fault("spd_trip", "solar installation", None, [], ["solar"], [
        ("medium", "the surge protection device shows it no longer provides protection after a storm, system still runs"),
    ]),
    Fault("smoke", "inverter or battery cabinet", None, [], ["solar", "battery"], [
        ("high", "burning or hot-plastic smell coming from the inverter or battery, possibly smoke - safety concern"),
    ]),
    Fault("wallbox", "EV wallbox", None, [], ["commissioning"], [
        ("medium", "car stops charging after a few minutes, wrong LED colour or communication timeout"),
    ]),
]

# Off-catalogue codes: the model must extract codes it has never seen in known_issues.md.
UNKNOWN_CODES: Dict[str, Dict[str, object]] = {
    "Huawei": {"equipment": "solar inverter", "codes": ["2064", "HUA-2064"], "skills": ["solar"]},
    "SMA": {"equipment": "solar inverter", "codes": ["3601", "SMA-3601"], "skills": ["solar"]},
    "Fronius": {"equipment": "solar inverter", "codes": ["306", "State 306"], "skills": ["solar"]},
    "Goodwe": {"equipment": "home battery storage", "codes": ["GOO-208", "208"], "skills": ["battery"]},
    "Vaillant": {"equipment": "heat pump", "codes": ["F.75", "F28"], "skills": ["heatpump"]},
    "Viessmann": {"equipment": "heat pump", "codes": ["A4", "F4"], "skills": ["heatpump"]},
}
UNKNOWN_STATES: List[State] = [
    ("high", "the device has stopped working completely"),
    ("medium", "the device runs but with reduced performance and an intermittent fault"),
]

ADMIN_TOPICS: Dict[str, List[str]] = {
    "billing": [
        "the latest invoice amount looks too high",
        "the feed-in payment for last quarter has not arrived",
        "the direct debit was taken twice this month",
        "the annual statement is unclear and the customer wants an explanation",
        "the monthly maintenance contract price changed without notice",
    ],
    "reschedule": [
        "the customer wants to move the maintenance appointment to another day",
        "the customer cannot be home for the technician visit and needs a new slot",
        "the customer wants to cancel the appointment and book one next month",
        "the customer asks for an earlier appointment than the one confirmed",
    ],
    "general": [
        "the customer asks how long the warranty on the system lasts",
        "the customer asks how to read the monitoring app or reset the portal password",
        "the customer asks about expanding the system with a battery or more panels",
        "the customer asks whether a service contract is worth it",
        "the customer asks for the documents or manual for the system",
    ],
}

STYLES_LENGTH = ["very short, 1-2 sentences", "medium length, a short paragraph",
                 "long and rambling with some irrelevant details"]
STYLES_TONE = [
    "polite and formal", "angry and impatient", "typos and no capitalisation",
    "abbreviations and slang", "contains pasted text from the monitoring app",
    "non-native speaker with grammar mistakes",
]
STYLES_PHONE = [
    "speech-to-text transcript with filler words and almost no punctuation",
    "speech-to-text transcript with a few misheard words",
]


@dataclass
class Spec:
    id: str
    scenario: str
    hard: bool
    label: Dict[str, object]
    gen: Dict[str, object] = field(default_factory=dict)


def _pick_state(rng: random.Random, states: List[State]) -> State:
    return rng.choice(states)


def _gen_common(rng: random.Random) -> Dict[str, object]:
    channel = rng.choices(["email", "phone-transcript"], weights=[0.7, 0.3])[0]
    language = "en" if rng.random() < EN_SHARE else "de"
    mixed = rng.random() < 0.2  # dominant language stays the label
    if channel == "phone-transcript":
        styles = [rng.choice(STYLES_PHONE)]
    else:  # one length style + one tone style, so they cannot contradict
        styles = [rng.choice(STYLES_LENGTH), rng.choice(STYLES_TONE)]
    return {"channel": channel, "language": language, "mixed": mixed,
            "styles": styles, "region": rng.choice(REGIONS)}


def _fault_spec(rng: random.Random, idx: int, hard: bool, scenario: str,
                equipment: str, manufacturer: Optional[str], code: Optional[str],
                skills: List[str], state: State, mention_brand: bool,
                admin_wrapper: Optional[str] = None) -> Spec:
    severity, situation = state
    gen = _gen_common(rng)
    gen.update({
        "equipment": equipment, "situation": situation,
        "code": code, "brand": manufacturer if mention_brand else None,
        "admin_wrapper": admin_wrapper,
    })
    label = {
        "error_code": code,
        "manufacturer": manufacturer if mention_brand else None,
        "severity": severity, "intent": "fault",
        "required_skills": list(skills), "detected_language": gen["language"],
    }
    return Spec(f"t{idx:05d}", scenario, hard, label, gen)


def sample_spec(rng: random.Random, idx: int) -> Spec:
    r = rng.random()
    if r < 0.50:  # catalogue fault, usually with code
        f = rng.choice(FAULTS[:9]) if rng.random() < 0.8 else rng.choice(FAULTS)
        code = rng.choice(f.codes) if (f.codes and rng.random() < 0.8) else None
        mention_brand = bool(f.manufacturer) and rng.random() < 0.85
        return _fault_spec(rng, idx, False, f.key, f.equipment, f.manufacturer, code,
                           f.skills, _pick_state(rng, f.states), mention_brand)
    if r < 0.62:  # unknown code (hard)
        brand = rng.choice(list(UNKNOWN_CODES))
        u = UNKNOWN_CODES[brand]
        return _fault_spec(rng, idx, True, f"unknown_code_{brand.lower()}", u["equipment"],  # type: ignore[arg-type]
                           brand, rng.choice(u["codes"]), u["skills"],  # type: ignore[arg-type]
                           _pick_state(rng, UNKNOWN_STATES), True)
    if r < 0.88:  # administrative
        intent = rng.choices(["billing", "reschedule", "general"], weights=[0.3, 0.4, 0.3])[0]
        gen = _gen_common(rng)
        brand = rng.choice(["Huawei", "SMA", "Fronius", "Goodwe", "Vaillant", "Viessmann"]) \
            if rng.random() < 0.25 else None
        gen.update({"intent": intent, "topic": rng.choice(ADMIN_TOPICS[intent]), "brand": brand,
                    "equipment": UNKNOWN_CODES[brand]["equipment"] if brand else None})
        label = {"error_code": None, "manufacturer": brand, "severity": "low",
                 "intent": intent, "required_skills": [], "detected_language": gen["language"]}
        return Spec(f"t{idx:05d}", f"admin_{intent}", False, label, gen)
    # hard: administrative ticket that also reports a fault => intent must be "fault"
    f = rng.choice(FAULTS)
    wrapper = rng.choice(["billing", "reschedule", "general"])
    topic = rng.choice(ADMIN_TOPICS[wrapper])
    mention_brand = bool(f.manufacturer) and rng.random() < 0.6
    code = rng.choice(f.codes) if (f.codes and rng.random() < 0.5) else None
    return _fault_spec(rng, idx, True, f"mixed_{wrapper}_{f.key}", f.equipment, f.manufacturer,
                       code, f.skills, _pick_state(rng, f.states), mention_brand,
                       admin_wrapper=topic)


def sample_specs(n: int, seed: int) -> List[Spec]:
    rng = random.Random(seed)
    return [sample_spec(rng, i) for i in range(n)]
