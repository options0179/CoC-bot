import json
from unittest.mock import MagicMock

import pytest

import intent_analyzer
from intent_analyzer import IntentResult, analyze_intent, build_prompt, parse_intent_response


def test_parses_valid_response():
    raw = json.dumps({
        "action_summary": "책상 서랍 밑바닥을 유심히 더듬는다",
        "intent_type": "skill_check",
        "purpose": "숨겨진 물건이나 장치를 찾으려 함",
        "target_object": "책상 서랍",
        "confidence": 0.9,
    })

    result = parse_intent_response(raw)

    assert isinstance(result, IntentResult)
    assert result.action_summary == "책상 서랍 밑바닥을 유심히 더듬는다"
    assert result.purpose == "숨겨진 물건이나 장치를 찾으려 함"


def test_no_longer_judges_whether_a_check_is_needed():
    # 판정 필요 여부/대상 스킬은 더 이상 Gemini가 판단하지 않는다.
    assert "requires_roll" not in intent_analyzer.RESPONSE_SCHEMA["properties"]
    assert "target_skill" not in intent_analyzer.RESPONSE_SCHEMA["properties"]
    assert not hasattr(intent_analyzer, "COC_SKILLS")
    assert not hasattr(IntentResult("", "none", "", "", 0.0), "requires_roll")


def test_ignores_legacy_roll_fields_in_response():
    raw = json.dumps({
        "intent_type": "skill_check",
        "purpose": "x",
        "requires_roll": True,
        "target_skill": "관찰력",
    })

    result = parse_intent_response(raw)

    assert result.purpose == "x"


def test_rejects_unknown_intent_type():
    raw = json.dumps({"intent_type": "not_a_real_type", "purpose": "x"})

    with pytest.raises(ValueError):
        parse_intent_response(raw)


def test_rejects_missing_required_field():
    raw = json.dumps({
        "intent_type": "skill_check",
        # missing "purpose"
    })

    with pytest.raises(ValueError, match="필수 필드가 없습니다"):
        parse_intent_response(raw)


def test_rejects_wrong_type_confidence():
    raw = json.dumps({
        "intent_type": "skill_check",
        "purpose": "x",
        "confidence": "high",  # should be number, not string
    })

    with pytest.raises(ValueError, match="confidence는 숫자여야 합니다"):
        parse_intent_response(raw)


def test_build_prompt_includes_scene_and_input():
    prompt = build_prompt("문을 연다", "어두운 복도")

    assert "문을 연다" in prompt
    assert "어두운 복도" in prompt


def test_analyze_intent_uses_injected_model_and_parses_response():
    fake_model = MagicMock()
    fake_model.generate_content.return_value = MagicMock(text=json.dumps({
        "intent_type": "movement",
        "purpose": "복도로 이동",
    }))

    result = analyze_intent("복도로 걸어간다", "어두운 복도", model=fake_model)

    fake_model.generate_content.assert_called_once()
    assert result.purpose == "복도로 이동"
