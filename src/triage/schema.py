"""Triage output contract, mirroring Smart Dispatcher's `record_triage_diagnosis` tool.

Source: Smart-dispatcher-Agent / src/empire_dispatcher/graph/nodes.py
Differences from the original tool schema (deliberate, to make evaluation exact):
  - required_skills is restricted to the skill tags used in technicians.csv.
  - error_code / manufacturer are always emitted (null when absent).
"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict

Manufacturer = Literal["Huawei", "SMA", "Fronius", "Goodwe", "Vaillant", "Viessmann"]
Severity = Literal["low", "medium", "high"]
Intent = Literal["fault", "billing", "reschedule", "general"]
Language = Literal["de", "en"]
Skill = Literal[
    "solar", "battery", "hybrid", "heatpump", "refrigerant",
    "brazing", "optimizer", "commissioning", "hydronic",
]

MANUFACTURERS: List[str] = list(Manufacturer.__args__)  # type: ignore[attr-defined]
SEVERITIES: List[str] = list(Severity.__args__)  # type: ignore[attr-defined]
INTENTS: List[str] = list(Intent.__args__)  # type: ignore[attr-defined]
SKILLS: List[str] = list(Skill.__args__)  # type: ignore[attr-defined]


class TriageDiagnosis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_code: Optional[str] = None
    manufacturer: Optional[Manufacturer] = None
    severity: Severity
    intent: Intent
    required_skills: List[Skill]
    detected_language: Language


# Verbatim from the Smart Dispatcher triage node.
TRIAGE_SYSTEM_PROMPT = (
    "You are the triage assistant for Empire, a German residential solar + heat-pump company. "
    "Your job is to read a (possibly messy, mixed German/English) customer ticket and extract a "
    "structured diagnosis. Respond with a single JSON object and nothing else.\n"
    "Rules:\n"
    '- "high" severity = customer has no power, no heat, smoke smell, or safety concern.\n'
    '- "medium" = degraded operation, intermittent fault.\n'
    '- "low" = informational / billing / reschedule.\n'
    '- If the message is purely administrative (rescheduling, billing question), use intent != "fault".\n'
    "Keys: error_code (string or null), manufacturer (Huawei|SMA|Fronius|Goodwe|Vaillant|Viessmann|null), "
    "severity (low|medium|high), intent (fault|billing|reschedule|general), "
    "required_skills (list of: solar, battery, hybrid, heatpump, refrigerant, brazing, optimizer, "
    "commissioning, hydronic), detected_language (de|en)."
)


def format_ticket(channel: str, subject: str, body: str) -> str:
    """The user-turn text the model sees. Keep identical for training and inference."""
    return f"Channel: {channel}\nSubject: {subject}\nBody: {body}"
