import json
from dataclasses import dataclass

MODEL_NAME = "gemini-2.5-flash"

_INTENT_TYPES = ["skill_check", "combat", "dialogue", "movement", "none"]

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "action_summary": {"type": "string"},
        "intent_type": {"type": "string", "enum": _INTENT_TYPES},
        "purpose": {"type": "string"},
        "target_object": {"type": "string"},
        "confidence": {"type": "number"},
    },
    "required": ["intent_type", "purpose"],
}


@dataclass
class IntentResult:
    action_summary: str
    intent_type: str
    purpose: str
    target_object: str
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

    # Validate confidence is a number if present
    confidence_value = data.get("confidence", 0.0)
    try:
        confidence = float(confidence_value)
    except (ValueError, TypeError):
        raise ValueError(f"confidence는 숫자여야 합니다: {confidence_value!r}")

    return IntentResult(
        action_summary=data.get("action_summary", ""),
        intent_type=intent_type,
        purpose=data["purpose"],
        target_object=data.get("target_object", ""),
        confidence=confidence,
    )


def build_prompt(player_input: str, scene_context: str) -> str:
    return (
        f"[현재 장면]\n{scene_context}\n\n"
        f"[플레이어 입력]\n{player_input}\n\n"
        "플레이어의 행동을 요약해 요청된 JSON 스키마로만 응답하라. "
        "판정이 필요한지 여부는 판단하지 말고, 무엇을 하려는 행동인지만 정리하라."
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
