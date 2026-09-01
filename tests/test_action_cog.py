import asyncio
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.action import ActionCog
from dice import CheckResult, SuccessLevel
from intent_analyzer import IntentResult


def _make_interaction(user_id=1, guild_id=10):
    interaction = MagicMock()
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.user.id = user_id
    interaction.guild_id = guild_id
    return interaction


def test_action_sends_narration_when_no_roll_required(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.action.analyze_intent",
        lambda text, scene_context: IntentResult(
            action_summary="주변을 둘러본다",
            intent_type="none",
            target_skill="unknown",
            purpose="상황 파악",
            target_object="",
            requires_roll=False,
            confidence=0.5,
        ),
    )
    cog = ActionCog(bot=MagicMock(pool="fake-pool"))
    interaction = _make_interaction()

    asyncio.run(cog.action.callback(cog, interaction, 설명="주변을 둘러본다"))

    interaction.followup.send.assert_awaited_once()
    _, kwargs = interaction.followup.send.call_args
    assert kwargs["embed"].title == "서술"


def test_action_rolls_check_when_skill_value_found(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.action.analyze_intent",
        lambda text, scene_context: IntentResult(
            action_summary="책상 서랍을 더듬는다",
            intent_type="skill_check",
            target_skill="관찰력",
            purpose="숨겨진 물건을 찾으려 함",
            target_object="책상 서랍",
            requires_roll=True,
            confidence=0.9,
        ),
    )
    mock_get_skill_value = AsyncMock(return_value=60)
    monkeypatch.setattr(
        "bot.cogs.action.get_skill_value",
        mock_get_skill_value,
    )
    monkeypatch.setattr(
        "bot.cogs.action.roll_check",
        lambda skill: CheckResult(roll=10, skill=skill, level=SuccessLevel.REGULAR),
    )
    cog = ActionCog(bot=MagicMock(pool="fake-pool"))
    interaction = _make_interaction(user_id=1, guild_id=10)

    asyncio.run(cog.action.callback(cog, interaction, 설명="책상 서랍을 더듬는다"))

    _, kwargs = interaction.followup.send.call_args
    assert kwargs["embed"].title == "관찰력 판정"
    mock_get_skill_value.assert_awaited_once_with("fake-pool", 10, 1, "관찰력")


def test_action_sends_ephemeral_message_when_skill_value_missing(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.action.analyze_intent",
        lambda text, scene_context: IntentResult(
            action_summary="자물쇠를 딴다",
            intent_type="skill_check",
            target_skill="열쇠공",
            purpose="문을 열려 함",
            target_object="문",
            requires_roll=True,
            confidence=0.8,
        ),
    )
    monkeypatch.setattr(
        "bot.cogs.action.get_skill_value",
        AsyncMock(return_value=None),
    )
    cog = ActionCog(bot=MagicMock(pool="fake-pool"))
    interaction = _make_interaction()

    asyncio.run(cog.action.callback(cog, interaction, 설명="자물쇠를 딴다"))

    _, kwargs = interaction.followup.send.call_args
    assert kwargs.get("ephemeral") is True


def test_action_sends_narration_when_requires_roll_but_skill_unknown(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.action.analyze_intent",
        lambda text, scene_context: IntentResult(
            action_summary="애매한 행동을 한다",
            intent_type="skill_check",
            target_skill="unknown",
            purpose="판단하기 어려움",
            target_object="",
            requires_roll=True,
            confidence=0.4,
        ),
    )
    mock_get_skill_value = AsyncMock()
    mock_roll_check = MagicMock()
    monkeypatch.setattr("bot.cogs.action.get_skill_value", mock_get_skill_value)
    monkeypatch.setattr("bot.cogs.action.roll_check", mock_roll_check)
    cog = ActionCog(bot=MagicMock(pool="fake-pool"))
    interaction = _make_interaction()

    asyncio.run(cog.action.callback(cog, interaction, 설명="애매한 행동을 한다"))

    _, kwargs = interaction.followup.send.call_args
    assert kwargs["embed"].title == "서술"
    mock_get_skill_value.assert_not_called()
    mock_roll_check.assert_not_called()


def test_action_sends_ephemeral_message_when_analyze_intent_raises_value_error(monkeypatch):
    def _raise(text, scene_context):
        raise ValueError("아무 메시지")

    monkeypatch.setattr("bot.cogs.action.analyze_intent", _raise)
    cog = ActionCog(bot=MagicMock(pool="fake-pool"))
    interaction = _make_interaction()

    asyncio.run(cog.action.callback(cog, interaction, 설명="칼로 찌른다"))

    interaction.followup.send.assert_awaited_once()
    _, kwargs = interaction.followup.send.call_args
    assert kwargs.get("ephemeral") is True
