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

    # Check for required fields
    required_fields = RESPONSE_SCHEMA["required"]
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValueError(f"필수 필드가 없습니다: {', '.join(missing_fields)}")

    intent_type = data["intent_type"]
    if intent_type not in _INTENT_TYPES:
        raise ValueError(f"알 수 없는 intent_type입니다: {intent_type}")

    target_skill = data["target_skill"]
    if target_skill not in SKILL_NAMES and target_skill != "unknown":
        raise ValueError(f"알 수 없는 target_skill입니다: {target_skill}")

    # Validate requires_roll is a boolean
    requires_roll_value = data["requires_roll"]
    if not isinstance(requires_roll_value, bool):
        raise ValueError(f"requires_roll은 boolean이어야 합니다: {requires_roll_value!r}")

    # Validate confidence is a number if present
    confidence_value = data.get("confidence", 0.0)
    try:
        confidence = float(confidence_value)
    except (ValueError, TypeError):
        raise ValueError(f"confidence는 숫자여야 합니다: {confidence_value!r}")

    return IntentResult(
        action_summary=data.get("action_summary", ""),
        intent_type=intent_type,
        target_skill=target_skill,
        purpose=data["purpose"],
        target_object=data.get("target_object", ""),
        requires_roll=requires_roll_value,
        confidence=confidence,
    )


def build_prompt(player_input: str, scene_context: str) -> str:
    return (
        f"[현재 장면]\n{scene_context}\n\n"
        f"[플레이어 입력]\n{player_input}\n\n"
        "플레이어의 행동을 분석해 요청된 JSON 스키마로만 응답하라. "
        "target_skill은 반드시 주어진 목록 중 하나여야 하며, "
        "판정이 불필요하면 requires_roll=false, target_skill='unknown'으로 응답하라."
    )


def _build_model():
    import google.generativeai as genai

    return genai.GenerativeModel(
        MODEL_NAME,
        generation_config={
            "response_mime_type": "application/json",
            "response_schema": RESPONSE_SCHEMA,
        },
    )


def analyze_intent(player_input: str, scene_context: str, model=None) -> IntentResult:
    model = model or _build_model()
    response = model.generate_content(build_prompt(player_input, scene_context))
    return parse_intent_response(response.text)
