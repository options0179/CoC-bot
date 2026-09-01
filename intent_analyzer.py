import json
from dataclasses import dataclass

from sheet_parser import SKILL_NAMES

MODEL_NAME = "gemini-2.5-flash"

COC_SKILLS = sorted(SKILL_NAMES)

_INTENT_TYPES = ["skill_check", "combat", "dialogue", "movement", "none"]

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "action_summary": {"type": "string"},
        "intent_type": {"type": "string", "enum": _INTENT_TYPES},
        "target_skill": {"type": "string", "enum": COC_SKILLS + ["unknown"]},
        "purpose": {"type": "string"},
        "target_object": {"type": "string"},
        "requires_roll": {"type": "boolean"},
        "confidence": {"type": "number"},
    },
    "required": ["intent_type", "target_skill", "purpose", "requires_roll"],
}


@dataclass
class IntentResult:
    action_summary: str
    intent_type: str
    target_skill: str
    purpose: str
    target_object: str
    requires_roll: bool
    confidence: float


def parse_intent_response(raw_json: str) -> IntentResult:
    data = json.loads(raw_json)
    intent_type = data["intent_type"]
    if intent_type not in _INTENT_TYPES:
        raise ValueError(f"알 수 없는 intent_type입니다: {intent_type}")
    target_skill = data["target_skill"]
    if target_skill not in SKILL_NAMES and target_skill != "unknown":
        raise ValueError(f"알 수 없는 target_skill입니다: {target_skill}")
    return IntentResult(
        action_summary=data.get("action_summary", ""),
        intent_type=intent_type,
        target_skill=target_skill,
        purpose=data["purpose"],
        target_object=data.get("target_object", ""),
        requires_roll=bool(data["requires_roll"]),
        confidence=float(data.get("confidence", 0.0)),
    )
