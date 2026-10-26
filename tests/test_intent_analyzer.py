import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from intent_analyzer import (
    COC_SKILLS,
    RESPONSE_SCHEMA,
    IntentResult,
    analyze_intent,
    build_prompt,
    parse_intent_response,
)
from sheet_parser import SKILL_NAMES


def test_coc_skills_matches_sheet_parser_skill_names():
    assert set(COC_SKILLS) == SKILL_NAMES


def test_parses_valid_skill_check_response():
    raw = json.dumps({
        "action_summary": "책상 서랍 밑바닥을 유심히 더듬는다",
        "intent_type": "skill_check",
        "target_skill": "관찰력",
        "purpose": "숨겨진 물건이나 장치를 찾으려 함",
        "target_object": "책상 서랍",
        "requires_roll": True,
        "confidence": 0.9,
        "check_id": "desk",
    })

    result = parse_intent_response(raw)

    assert isinstance(result, IntentResult)
    assert result.target_skill == "관찰력"
    assert result.requires_roll is True
    assert result.check_id == "desk"


def test_rejects_unknown_intent_type():
    raw = json.dumps({
        "intent_type": "not_a_real_type",
        "target_skill": "unknown",
        "purpose": "x",
        "requires_roll": False,
    })

    with pytest.raises(ValueError):
        parse_intent_response(raw)


def test_rejects_target_skill_not_in_enum():
    raw = json.dumps({
        "intent_type": "skill_check",
        "target_skill": "Spot Hidden",
        "purpose": "x",
        "requires_roll": True,
    })

    with pytest.raises(ValueError):
        parse_intent_response(raw)


def test_allows_unknown_target_skill_with_no_roll():
    raw = json.dumps({
        "intent_type": "none",
        "target_skill": "unknown",
        "purpose": "그냥 주변을 둘러본다",
        "requires_roll": False,
    })

    result = parse_intent_response(raw)

    assert result.target_skill == "unknown"
    assert result.requires_roll is False


def test_rejects_missing_required_field():
    raw = json.dumps({
        "intent_type": "skill_check",
        "target_skill": "관찰력",
        # missing "purpose"
        "requires_roll": True,
    })

    with pytest.raises(ValueError, match="필수 필드가 없습니다"):
        parse_intent_response(raw)


def test_rejects_non_object_json_response():
    with pytest.raises(ValueError, match="JSON 객체"):
        parse_intent_response("[]")


def test_rejects_empty_model_response():
    with pytest.raises(ValueError, match="응답이 비어"):
        parse_intent_response(None)


def test_rejects_wrong_type_requires_roll():
    raw = json.dumps({
        "intent_type": "skill_check",
        "target_skill": "관찰력",
        "purpose": "x",
        "requires_roll": "yes",  # should be boolean, not string
    })

    with pytest.raises(ValueError, match="requires_roll은 boolean이어야 합니다"):
        parse_intent_response(raw)


def test_rejects_wrong_type_confidence():
    raw = json.dumps({
        "intent_type": "skill_check",
        "target_skill": "관찰력",
        "purpose": "x",
        "requires_roll": True,
        "confidence": "high",  # should be number, not string
    })

    with pytest.raises(ValueError, match="confidence는 숫자여야 합니다"):
        parse_intent_response(raw)


def test_build_prompt_includes_scene_and_input():
    prompt = build_prompt("문을 연다", "어두운 복도")

    assert "문을 연다" in prompt
    assert "어두운 복도" in prompt


def test_prompt_lists_only_rule_ids_and_actions():
    prompt = build_prompt("서랍을 뒤진다", "서재", [{
        "id": "desk", "skill": "관찰력", "action": "서랍 조사",
        "success": "비밀 문서", "failure": "아무것도 없음",
    }])
    assert "desk" in prompt and "서랍 조사" in prompt
    assert "비밀 문서" not in prompt and "아무것도 없음" not in prompt
    assert "check_id" in prompt


def test_rejects_non_string_rule_id():
    raw = json.dumps({"intent_type": "skill_check", "target_skill": "관찰력",
                      "purpose": "조사", "requires_roll": True, "check_id": ["desk"]})
    with pytest.raises(ValueError, match="check_id"):
        parse_intent_response(raw)


def test_analyze_intent_rejects_safety_blocked_response():
    fake_client = MagicMock()
    response = MagicMock(text=None)
    response.prompt_feedback.block_reason.name = "SAFETY"
    fake_client.models.generate_content.return_value = response
    with pytest.raises(ValueError, match="안전"):
        analyze_intent("행동", "장면", model=fake_client)


def test_analyze_intent_rejects_empty_response_without_safety_block():
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = SimpleNamespace(text="", prompt_feedback=None)
    with pytest.raises(ValueError, match="비어"):
        analyze_intent("행동", "장면", model=fake_client)


def test_analyze_intent_rejects_candidate_safety_block():
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = SimpleNamespace(
        text=None, prompt_feedback=None,
        candidates=[SimpleNamespace(finish_reason=SimpleNamespace(name="SAFETY"))],
    )
    with pytest.raises(ValueError, match="안전"):
        analyze_intent("행동", "장면", model=fake_client)


def test_analyze_intent_uses_injected_model_and_parses_response():
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = MagicMock(text=json.dumps({
        "intent_type": "movement",
        "target_skill": "unknown",
        "purpose": "복도로 이동",
        "requires_roll": False,
    }))

    result = analyze_intent("복도로 걸어간다", "어두운 복도", model=fake_client)

    fake_client.models.generate_content.assert_called_once_with(
        model="gemini-3.8-flash",
        contents=build_prompt("복도로 걸어간다", "어두운 복도"),
        config={"response_mime_type": "application/json", "response_schema": RESPONSE_SCHEMA},
    )
    assert result.purpose == "복도로 이동"
    assert result.requires_roll is False
