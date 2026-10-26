import asyncio
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.narration import NarrationCog, NarrationView, _next_position, setup
from bot.embeds import scenario_embed
from storage import advance_narration_position, create_pool, create_scenario, get_scenario_by_title


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


def test_keeper_and_pc_same_discord_account_need_one_vote(monkeypatch):
    scenario = {
        "id": 1, "structure": _STRUCTURE, "current_scene_index": 0,
        "current_line_index": 0, "keeper_user_id": 100,
    }
    monkeypatch.setattr("bot.cogs.narration.get_scenario_by_channel", AsyncMock(return_value=scenario))
    monkeypatch.setattr("bot.cogs.narration.get_roster", AsyncMock(return_value=[{"discord_user_id": 100}]))
    monkeypatch.setattr("bot.cogs.narration.get_scenario_by_id", AsyncMock(return_value=scenario))
    advance = AsyncMock(return_value=True)
    monkeypatch.setattr("bot.cogs.narration.advance_narration_position", advance)
    cog = NarrationCog(bot=_make_bot())
    interaction = _make_interaction(user_id=100)

    asyncio.run(cog.start.callback(cog, interaction))
    view = interaction.response.send_message.call_args.kwargs["view"]
    assert view.eligible_user_ids == {100}
    assert view.required_votes == 1
    asyncio.run(view.advance.callback(_make_interaction(user_id=100)))
    advance.assert_awaited_once_with(cog.pool, 1, 0, 0, 0, 1)


def test_restart_registers_all_saved_positions_and_routes_current_and_old(monkeypatch, tmp_path):
    async def _run():
        database_path = str(tmp_path / "narration.sqlite3")
        pool = await create_pool(database_path)
        scenario_id = await create_scenario(pool, 1, "두 장면", 100, "https://x", _STRUCTURE)
        other_id = await create_scenario(pool, 1, "한 장면", 200, "https://y", [{"scene": "짧은 장면", "lines": ["끝"]}])
        assert await advance_narration_position(pool, scenario_id, 0, 0, 0, 1)
        await pool.close()
        pool = await create_pool(database_path)
        try:
            bot = MagicMock(pool=pool)
            bot.add_cog = AsyncMock()
            await setup(bot)
            bot.add_cog.assert_awaited_once()
            views = [call.args[0] for call in bot.add_view.call_args_list]
            assert len(views) == 4
            ids = {view.advance.custom_id for view in views}
            assert ids == {
                f"narration:{scenario_id}:0:0", f"narration:{scenario_id}:0:1",
                f"narration:{scenario_id}:1:0", f"narration:{other_id}:0:0",
            }
            assert all(view.is_persistent() for view in views)
            old = next(view for view in views if view.scenario_id == scenario_id and (view.scene_index, view.line_index) == (0, 0))
            old_click = _make_interaction(user_id=100)
            await old.advance.callback(old_click)
            old_click.response.send_message.assert_awaited_once_with("낭독이 이미 다음 위치로 이동했습니다.", ephemeral=True)
            assert old.votes == set()
            current = next(view for view in views if view.scenario_id == scenario_id and (view.scene_index, view.line_index) == (0, 1))
            assert current.votes == set()
            first = _make_interaction(user_id=100)
            await current.advance.callback(first)
            scenario = await get_scenario_by_title(pool, 1, "두 장면")
            assert (scenario["current_scene_index"], scenario["current_line_index"]) == (1, 0)
            stale_click = _make_interaction(user_id=100)
            await current.advance.callback(stale_click)
            stale_click.response.send_message.assert_awaited_once_with("낭독이 이미 다음 위치로 이동했습니다.", ephemeral=True)
            assert current.votes == {100}
            final = next(view for view in views if view.scenario_id == scenario_id and (view.scene_index, view.line_index) == (1, 0))
            await final.advance.callback(_make_interaction(user_id=100))
            completed = await get_scenario_by_title(pool, 1, "두 장면")
            assert (completed["current_scene_index"], completed["current_line_index"]) == (len(_STRUCTURE), 0)
            fields = {field.name: field.value for field in scenario_embed(completed, []).fields}
            assert fields["진행 위치"] == "완료"
        finally:
            await pool.close()
    asyncio.run(_run())
