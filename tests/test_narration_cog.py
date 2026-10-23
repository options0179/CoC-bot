import asyncio
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.narration import NarrationCog, NarrationView, _next_position


def _make_interaction(guild_id=1, user_id=100, channel_id=555):
    interaction = MagicMock()
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.guild_id = guild_id
    interaction.channel_id = channel_id
    interaction.user = MagicMock(id=user_id)
    return interaction


def _make_bot():
    bot = MagicMock()
    bot.pool = MagicMock()
    return bot


_STRUCTURE = [
    {"part": "제1부", "scene": "장면 1", "lines": ["문장1", "문장2"]},
    {"part": "제1부", "scene": "장면 2", "lines": ["문장3"]},
]


def test_next_position_advances_within_scene():
    assert _next_position(_STRUCTURE, 0, 0) == (0, 1)


def test_next_position_moves_to_next_scene():
    assert _next_position(_STRUCTURE, 0, 1) == (1, 0)


def test_next_position_returns_none_at_end():
    assert _next_position(_STRUCTURE, 1, 0) is None


def test_start_reports_when_channel_unbound(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.narration.get_scenario_by_channel", AsyncMock(return_value=None)
    )
    cog = NarrationCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.start.callback(cog, interaction))

    interaction.response.send_message.assert_awaited_once_with(
        "이 채널에 배정된 시나리오가 없습니다.", ephemeral=True
    )


def test_start_reports_when_narration_exhausted(monkeypatch):
    scenario = {
        "id": 1, "structure": _STRUCTURE, "current_scene_index": 2,
        "current_line_index": 0, "keeper_user_id": 100,
    }
    monkeypatch.setattr(
        "bot.cogs.narration.get_scenario_by_channel", AsyncMock(return_value=scenario)
    )
    cog = NarrationCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.start.callback(cog, interaction))

    interaction.response.send_message.assert_awaited_once_with(
        "낭독할 내용이 남아있지 않습니다.", ephemeral=True
    )


def test_start_rejects_non_participant(monkeypatch):
    scenario = {
        "id": 1, "structure": _STRUCTURE, "current_scene_index": 0,
        "current_line_index": 0, "keeper_user_id": 100,
    }
    monkeypatch.setattr(
        "bot.cogs.narration.get_scenario_by_channel", AsyncMock(return_value=scenario)
    )
    monkeypatch.setattr(
        "bot.cogs.narration.get_roster",
        AsyncMock(return_value=[{"discord_user_id": 101}]),
    )
    cog = NarrationCog(bot=_make_bot())
    interaction = _make_interaction(user_id=999)

    asyncio.run(cog.start.callback(cog, interaction))

    interaction.response.send_message.assert_awaited_once_with(
        "키퍼 또는 시나리오 참가 PC만 낭독을 시작할 수 있습니다.", ephemeral=True
    )


def test_start_sends_current_line_with_pc_and_keeper_voters(monkeypatch):
    scenario = {
        "id": 1, "structure": _STRUCTURE, "current_scene_index": 0,
        "current_line_index": 0, "keeper_user_id": 100,
    }
    monkeypatch.setattr(
        "bot.cogs.narration.get_scenario_by_channel", AsyncMock(return_value=scenario)
    )
    monkeypatch.setattr(
        "bot.cogs.narration.get_roster",
        AsyncMock(return_value=[{"discord_user_id": 101}, {"discord_user_id": 102}]),
    )
    cog = NarrationCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.start.callback(cog, interaction))

    interaction.response.send_message.assert_awaited_once()
    _, kwargs = interaction.response.send_message.call_args
    assert kwargs["embed"].description == "문장1"
    assert isinstance(kwargs["view"], NarrationView)
    assert kwargs["view"].eligible_user_ids == {100, 101, 102}
