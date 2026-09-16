import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import bot.cogs.action as action_module
from bot.cogs.action import ActionCog


def _make_interaction(user_id=1, guild_id=10):
    interaction = MagicMock()
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.user.id = user_id
    interaction.guild_id = guild_id
    return interaction


def _stub_intent(monkeypatch, **fields):
    """analyze_intent가 어떤 필드를 돌려주든 /행동은 서술만 해야 한다.

    과거 Gemini 응답에 있던 requires_roll/target_skill을 그대로 실어 보내도
    판정이 트리거되지 않는지 확인하기 위해 SimpleNamespace로 흉내 낸다.
    """
    base = {
        "action_summary": "책상 서랍을 더듬는다",
        "intent_type": "skill_check",
        "purpose": "숨겨진 물건을 찾으려 함",
        "target_object": "책상 서랍",
        "confidence": 0.9,
    }
    base.update(fields)
    monkeypatch.setattr(
        action_module, "analyze_intent", lambda text, scene_context: SimpleNamespace(**base)
    )


def test_action_sends_narration_for_plain_description(monkeypatch):
    _stub_intent(monkeypatch, action_summary="주변을 둘러본다", intent_type="none")
    cog = ActionCog(bot=MagicMock(pool="fake-pool"))
    interaction = _make_interaction()

    asyncio.run(cog.action.callback(cog, interaction, 설명="주변을 둘러본다"))

    interaction.followup.send.assert_awaited_once()
    _, kwargs = interaction.followup.send.call_args
    assert kwargs["embed"].title == "서술"


def test_action_never_triggers_a_check_even_for_roll_worthy_action(monkeypatch):
    # 예전 구현이라면 requires_roll=True + target_skill으로 자동 판정을 굴렸을 입력.
    _stub_intent(monkeypatch, requires_roll=True, target_skill="관찰력")
    cog = ActionCog(bot=MagicMock(pool="fake-pool"))
    interaction = _make_interaction()

    asyncio.run(cog.action.callback(cog, interaction, 설명="책상 서랍을 더듬는다"))

    interaction.followup.send.assert_awaited_once()
    _, kwargs = interaction.followup.send.call_args
    assert kwargs["embed"].title == "서술"


def test_action_module_no_longer_depends_on_check_rolling():
    # 판정 트리거 경로 자체가 사라졌으므로 판정 관련 심볼도 남아 있으면 안 된다.
    assert not hasattr(action_module, "roll_check")
    assert not hasattr(action_module, "get_skill_value")
    assert not hasattr(action_module, "check_embed")


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
