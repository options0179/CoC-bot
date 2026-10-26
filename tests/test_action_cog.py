import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.cogs.action import ActionCog
from dice import CheckResult, SuccessLevel
from intent_analyzer import IntentResult
from scenario_parser import parse_scenario_html


RULE = {"id": "desk", "skill": "관찰력", "action": "서랍 조사",
        "success": "문서를 발견한다", "failure": "문서를 찾지 못한다"}
SCENARIO = {"id": 7, "guild_id": 10, "title": "관측소", "current_scene_index": 0,
            "current_line_index": 0,
            "structure": [{"scene": "서재", "lines": ["책상이 있다."], "checks": [RULE]}]}


def _interaction():
    interaction = MagicMock()
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.user.id = 1
    interaction.guild_id = 10
    interaction.channel_id = 99
    return interaction


def _intent(check_id="desk", confidence=0.9, requires_roll=True, skill="관찰력"):
    return IntentResult("서랍을 뒤진다", "skill_check", skill, "조사", "서랍",
                        requires_roll, confidence, check_id)


def _setup(monkeypatch, scenario=SCENARIO, intent=None, skill=60):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_scenario = AsyncMock(return_value=scenario)
    get_roster = AsyncMock(return_value=[{"discord_user_id": 1}])
    get_skill = AsyncMock(return_value=skill)
    analyze = MagicMock(return_value=intent or _intent())
    roll = MagicMock(return_value=CheckResult(roll=35, skill=60, level=SuccessLevel.REGULAR))
    monkeypatch.setattr("bot.cogs.action.get_scenario_by_channel", get_scenario)
    monkeypatch.setattr("bot.cogs.action.get_roster", get_roster)
    monkeypatch.setattr("bot.cogs.action.get_skill_value", get_skill)
    monkeypatch.setattr("bot.cogs.action.analyze_intent", analyze)
    monkeypatch.setattr("bot.cogs.action.roll_check", roll)
    return get_scenario, get_roster, get_skill, analyze, roll


def _run():
    interaction = _interaction()
    cog = ActionCog(bot=MagicMock(pool="fake-pool"))
    asyncio.run(cog.action.callback(cog, interaction, 설명="서랍을 뒤진다"))
    return interaction


def test_action_uses_current_scene_rule_and_registered_skill(monkeypatch):
    _, _, get_skill, analyze, roll = _setup(monkeypatch, intent=_intent(skill="심리학"))
    interaction = _run()
    assert "서재" in analyze.call_args.args[1]
    assert "책상이 있다" in analyze.call_args.args[1]
    assert analyze.call_args.args[2] == [RULE]
    get_skill.assert_awaited_once_with("fake-pool", 10, 1, "관찰력")
    roll.assert_called_once_with(60)
    embed = interaction.followup.send.call_args.kwargs["embed"]
    assert embed.title == "관찰력 판정"
    assert any("문서를 발견한다" in field.value for field in embed.fields)


@pytest.mark.parametrize(
    "level,roll_value,branch_text",
    [(SuccessLevel.HARD, 21, "숨소리를 듣는다."),
     (SuccessLevel.FAIL, 84, "발소리를 들킨다.")],
)
def test_google_docs_check_flows_through_action_to_matching_skill_and_story_branch(
    monkeypatch, level, roll_value, branch_text
):
    html = """
    <h1>유리파 관측소</h1><h2>장면 1: 잠긴 문</h2>
    <h3>Keeper 낭독</h3><p>문틈으로 불빛이 샌다.</p>
    <h3>Checks</h3><table><tbody>
      <tr><th>id</th><th>skill</th><th>action</th><th>success</th><th>failure</th></tr>
      <tr><td>door-listen</td><td>관찰력</td><td>문 너머를 듣는다.</td>
          <td>숨소리를 듣는다.</td><td>발소리를 들킨다.</td></tr>
    </tbody></table>
    """
    parsed = parse_scenario_html(html)
    scenario = {**SCENARIO, "title": "유리파 관측소", "structure": parsed}
    intent = _intent(check_id="door-listen", skill="관찰력")
    _, _, get_skill, analyze, roll = _setup(monkeypatch, scenario=scenario, intent=intent, skill=72)
    roll.return_value = CheckResult(roll=roll_value, skill=72, level=level)

    interaction = _run()

    assert analyze.call_args.args[1] == "유리파 관측소 / 장면 1: 잠긴 문\n문틈으로 불빛이 샌다."
    assert analyze.call_args.args[2] == parsed[0]["checks"]
    get_skill.assert_awaited_once_with("fake-pool", 10, 1, "관찰력")
    roll.assert_called_once_with(72)
    embed = interaction.followup.send.call_args.kwargs["embed"]
    assert embed.title == "관찰력 판정"
    assert any(branch_text in field.value for field in embed.fields)


def test_action_rolls_registered_rule_even_when_model_says_no_roll(monkeypatch):
    _, _, _, _, roll = _setup(monkeypatch, intent=_intent(requires_roll=False))
    interaction = _run()
    roll.assert_called_once_with(60)
    assert interaction.followup.send.call_args.kwargs["embed"].title == "관찰력 판정"


@pytest.mark.parametrize("level,branch", [
    (SuccessLevel.CRITICAL, "success"), (SuccessLevel.EXTREME, "success"),
    (SuccessLevel.HARD, "success"), (SuccessLevel.REGULAR, "success"),
    (SuccessLevel.FAIL, "failure"), (SuccessLevel.FUMBLE, "failure"),
])
def test_action_selects_story_branch_from_dice_level(monkeypatch, level, branch):
    _, _, _, _, roll = _setup(monkeypatch)
    roll.return_value = CheckResult(roll=99 if branch == "failure" else 1,
                                    skill=60, level=level)
    interaction = _run()
    embed = interaction.followup.send.call_args.kwargs["embed"]
    assert any(RULE[branch] in field.value for field in embed.fields)


@pytest.mark.parametrize("scenario,intent", [
    (None, _intent()),
    ({**SCENARIO, "structure": [{"scene": "서재", "lines": ["책상"], "checks": []}]}, _intent()),
    (SCENARIO, _intent(check_id="")),
    (SCENARIO, _intent(check_id="unknown")),
    (SCENARIO, _intent(confidence=0.59)),
])
def test_action_refuses_unverified_rule_without_rolling(monkeypatch, scenario, intent):
    _, _, get_skill, _, roll = _setup(monkeypatch, scenario=scenario, intent=intent)
    interaction = _run()
    assert "/판정" in interaction.followup.send.call_args.args[0]
    get_skill.assert_not_awaited()
    roll.assert_not_called()


@pytest.mark.parametrize("skill", [None, -1, 101, True, "60"])
def test_action_refuses_missing_or_invalid_sheet_value(monkeypatch, skill):
    _, _, _, _, roll = _setup(monkeypatch, skill=skill)
    interaction = _run()
    assert "/판정" in interaction.followup.send.call_args.args[0]
    roll.assert_not_called()


def test_action_requires_participant_pc(monkeypatch):
    _, roster, _, _, roll = _setup(monkeypatch)
    roster.return_value = [{"discord_user_id": 2}]
    interaction = _run()
    assert "/판정" in interaction.followup.send.call_args.args[0]
    roll.assert_not_called()


def test_action_refuses_rule_with_unregistered_skill(monkeypatch):
    invalid = {**SCENARIO, "structure": [{"scene": "서재", "lines": ["책상"],
                                             "checks": [{**RULE, "skill": "위조 기능"}]}]}
    _, _, get_skill, _, roll = _setup(monkeypatch, scenario=invalid)
    interaction = _run()
    assert "/판정" in interaction.followup.send.call_args.args[0]
    get_skill.assert_not_awaited()
    roll.assert_not_called()


def test_action_refuses_roll_if_scene_moves_during_analysis(monkeypatch):
    get_scenario, _, _, _, roll = _setup(monkeypatch)
    get_scenario.side_effect = [SCENARIO, {**SCENARIO, "current_line_index": 1}]
    interaction = _run()
    assert "장면이 이동" in interaction.followup.send.call_args.args[0]
    roll.assert_not_called()


def test_action_refuses_roll_if_scene_moves_while_reading_skill(monkeypatch):
    get_scenario, _, get_skill, _, roll = _setup(monkeypatch)
    moved = False

    async def read_skill(*args):
        nonlocal moved
        moved = True
        return 60

    async def current_scenario(*args):
        return {**SCENARIO, "current_line_index": 1} if moved else SCENARIO

    get_skill.side_effect = read_skill
    get_scenario.side_effect = current_scenario
    interaction = _run()
    get_skill.assert_awaited_once()
    assert "장면이 이동" in interaction.followup.send.call_args.args[0]
    roll.assert_not_called()


def test_action_preserves_non_check_narration(monkeypatch):
    _setup(monkeypatch, scenario=None, intent=_intent(check_id="", requires_roll=False))
    interaction = _run()
    assert interaction.followup.send.call_args.kwargs["embed"].title == "서술"


@pytest.mark.parametrize("error,expected", [
    ("empty", "비어"), ("blocked", "안전"),
])
def test_action_distinguishes_empty_and_blocked(monkeypatch, error, expected):
    from intent_analyzer import IntentResponseBlocked, IntentResponseEmpty

    _, _, _, analyze, roll = _setup(monkeypatch)
    analyze.side_effect = (IntentResponseEmpty("secret") if error == "empty"
                           else IntentResponseBlocked("secret"))
    interaction = _run()
    assert expected in interaction.followup.send.call_args.args[0]
    roll.assert_not_called()


@pytest.mark.parametrize("error,expected", [
    (ValueError("secret response"), "형식"),
    (TimeoutError("secret timeout"), "연결"),
    (ConnectionError("secret network"), "연결"),
])
def test_action_sanitizes_analyzer_errors(monkeypatch, error, expected, caplog):
    _, _, _, analyze, roll = _setup(monkeypatch)
    analyze.side_effect = error
    interaction = _run()
    message = interaction.followup.send.call_args.args[0]
    assert expected in message
    assert "secret" not in message and "secret" not in caplog.text
    roll.assert_not_called()
    assert analyze.call_count == 1


@pytest.mark.parametrize("status,expected", [(401, "인증"), (403, "인증"),
                                               (429, "제한"), (503, "서비스")])
def test_action_classifies_provider_status_without_retry(monkeypatch, status, expected, caplog):
    class ProviderError(Exception):
        code = status

    _, _, _, analyze, roll = _setup(monkeypatch)
    analyze.side_effect = ProviderError("secret key and request")
    interaction = _run()
    message = interaction.followup.send.call_args.args[0]
    assert expected in message
    assert "secret" not in message and "secret" not in caplog.text
    assert analyze.call_count == 1
    roll.assert_not_called()


def test_action_reports_missing_key_without_analysis(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    analyze = MagicMock()
    monkeypatch.setattr("bot.cogs.action.analyze_intent", analyze)
    interaction = _run()
    interaction.response.send_message.assert_awaited_once()
    analyze.assert_not_called()


def test_action_classifies_model_not_found_without_retry(monkeypatch, caplog):
    class ProviderError(Exception):
        code = 404

    _, _, _, analyze, roll = _setup(monkeypatch)
    analyze.side_effect = ProviderError("secret request content")
    interaction = _run()

    message = interaction.followup.send.call_args.args[0]
    assert "모델" in message and "확인" in message
    assert "secret" not in message and "secret" not in caplog.text
    assert "model_not_found" in caplog.text
    assert analyze.call_count == 1
    roll.assert_not_called()
