import json

import pytest

from intent_analyzer import COC_SKILLS, IntentResult, parse_intent_response
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
    })

    result = parse_intent_response(raw)

    assert isinstance(result, IntentResult)
    assert result.target_skill == "관찰력"
    assert result.requires_roll is True


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
