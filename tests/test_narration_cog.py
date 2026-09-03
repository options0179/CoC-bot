import asyncio
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.narration import NarrationCog, _next_position


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


def test_start_sends_first_line_embed(monkeypatch):
    scenario = {
        "id": 1, "structure": _STRUCTURE, "current_scene_index": 0,
        "current_line_index": 0, "keeper_user_id": 100,
    }
    monkeypatch.setattr(
        "bot.cogs.narration.get_scenario_by_channel", AsyncMock(return_value=scenario)
    )
    monkeypatch.setattr("bot.cogs.narration.get_roster", AsyncMock(return_value=[]))

    class _NeverEndingView:
        async def wait(self):
            await asyncio.sleep(3600)

    monkeypatch.setattr(
        "bot.cogs.narration.NarrationView", lambda *a, **k: _NeverEndingView()
    )
    cog = NarrationCog(bot=_make_bot())
    interaction = _make_interaction()

    async def _run_with_timeout():
        task = asyncio.ensure_future(cog.start.callback(cog, interaction))
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(_run_with_timeout())

    interaction.response.send_message.assert_awaited_once()
    _, kwargs = interaction.response.send_message.call_args
    assert kwargs["embed"].title == "장면 1"
    assert kwargs["embed"].description == "문장1"


def test_start_advances_to_next_line_after_vote(monkeypatch):
    scenario = {
        "id": 1, "structure": _STRUCTURE, "current_scene_index": 0,
        "current_line_index": 0, "keeper_user_id": 100,
    }
    monkeypatch.setattr(
        "bot.cogs.narration.get_scenario_by_channel", AsyncMock(return_value=scenario)
    )
    monkeypatch.setattr("bot.cogs.narration.get_roster", AsyncMock(return_value=[]))
    advance_mock = AsyncMock()
    monkeypatch.setattr("bot.cogs.narration.advance_narration_position", advance_mock)

    class _OneShotView:
        _created = 0

        def __init__(self, *a, **k):
            _OneShotView._created += 1
            self._n = _OneShotView._created

        async def wait(self):
            if self._n == 1:
                return False
            await asyncio.sleep(3600)

    monkeypatch.setattr("bot.cogs.narration.NarrationView", _OneShotView)
    cog = NarrationCog(bot=_make_bot())
    interaction = _make_interaction()

    async def _run_with_timeout():
        task = asyncio.ensure_future(cog.start.callback(cog, interaction))
        await asyncio.sleep(0.05)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(_run_with_timeout())

    advance_mock.assert_awaited_once_with(cog.pool, 1, 0, 1)
    interaction.followup.send.assert_awaited_once()
    _, kwargs = interaction.followup.send.call_args
    assert kwargs["embed"].description == "문장2"
