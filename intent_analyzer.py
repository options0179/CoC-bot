import json
import math
from dataclasses import dataclass

from skill_names import SKILL_NAMES

MODEL_NAME = "gemini-3.8-flash"

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
        "check_id": {"type": "string"},
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
    check_id: str = ""


class IntentResponseEmpty(ValueError):
    pass


class IntentResponseBlocked(ValueError):
    pass


def parse_intent_response(raw_json: str) -> IntentResult:
    if not isinstance(raw_json, str) or not raw_json.strip():
        raise IntentResponseEmpty("Gemini 응답이 비어 있습니다.")
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        raise ValueError("Gemini 응답 JSON 형식이 올바르지 않습니다.") from None
    if not isinstance(data, dict):
        raise ValueError("Gemini 응답은 JSON 객체여야 합니다.")

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

    check_id = data.get("check_id", "")
    if not isinstance(check_id, str):
        raise ValueError("check_id는 문자열이어야 합니다.")

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
    if not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise ValueError("confidence는 0~1 사이여야 합니다.")

    for name in ("action_summary", "purpose", "target_object"):
        if name in data and not isinstance(data[name], str):
            raise ValueError(f"{name}은 문자열이어야 합니다.")

    return IntentResult(
        action_summary=data.get("action_summary", ""),
        intent_type=intent_type,
        target_skill=target_skill,
        purpose=data["purpose"],
        target_object=data.get("target_object", ""),
        requires_roll=requires_roll_value,
        confidence=confidence,
        check_id=check_id,
    )


def build_prompt(player_input: str, scene_context: str, checks: list[dict] | None = None) -> str:
    prompt = (
        f"[현재 장면]\n{scene_context}\n\n"
        f"[플레이어 입력]\n{player_input}\n\n"
        "플레이어의 행동을 분석해 요청된 JSON 스키마로만 응답하라. "
        "target_skill은 반드시 주어진 목록 중 하나여야 하며, "
        "판정이 불필요하면 requires_roll=false, target_skill='unknown'으로 응답하라."
    )
    candidates = [{"id": check["id"], "action": check["action"]} for check in checks or []]
    return (prompt + "\n[현재 장면 판정 후보]\n" + json.dumps(candidates, ensure_ascii=False)
            + "\n행동이 후보 하나와 명확히 일치할 때만 정확한 check_id를 선택하라. "
            "일치하는 후보가 없거나 모호하면 check_id=''로 응답하라. "
            "주사위 결과와 성공·실패 이야기를 만들지 마라.")


def _build_client():
    from google import genai

    return genai.Client()


def analyze_intent(player_input: str, scene_context: str, checks: list[dict] | None = None, model=None) -> IntentResult:
    client = model or _build_client()
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=build_prompt(player_input, scene_context, checks),
        config={"response_mime_type": "application/json", "response_schema": RESPONSE_SCHEMA},
    )
    try:
        raw = response.text
    except ValueError:
        raw = None
    if not raw:
        feedback = getattr(response, "prompt_feedback", None)
        reason = getattr(feedback, "block_reason", None)
        blocked = reason and getattr(reason, "name", "") in (
            "SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII"
        )
        if not blocked:
            blocked = any(getattr(getattr(candidate, "finish_reason", None), "name", "") in (
                "SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII"
            ) for candidate in (getattr(response, "candidates", None) or []))
        if blocked:
            raise IntentResponseBlocked("Gemini 안전 필터가 응답을 차단했습니다.")
    return parse_intent_response(raw)
