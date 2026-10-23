import asyncio
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.narration import NarrationView


_STRUCTURE = [
    {"part": "제1부", "scene": "장면 1", "lines": ["문장1"]},
    {"part": "제1부", "scene": "장면 2", "lines": ["문장2"]},
]


def _make_interaction(user_id):
    interaction = MagicMock()
    interaction.response = AsyncMock()
    interaction.user = MagicMock(id=user_id)
    return interaction


def _view(eligible_user_ids={1, 2, 3}):
    return NarrationView(
        pool="pool",
        scenario_id=9,
        structure=_STRUCTURE,
        scene_index=0,
        line_index=0,
        eligible_user_ids=eligible_user_ids,
    )


def test_non_participant_vote_rejected():
    view = _view()
    interaction = _make_interaction(user_id=99)

    asyncio.run(view.advance.callback(interaction))

    interaction.response.send_message.assert_awaited_once_with(
        "시나리오 참가자만 투표할 수 있습니다.", ephemeral=True
    )
    assert view.votes == set()


def test_duplicate_vote_does_not_count_twice(monkeypatch):
    advance = AsyncMock(return_value=True)
    monkeypatch.setattr("bot.cogs.narration.advance_narration_position", advance)
    view = _view()

    asyncio.run(view.advance.callback(_make_interaction(user_id=1)))
    duplicate = _make_interaction(user_id=1)
    asyncio.run(view.advance.callback(duplicate))

    assert view.votes == {1}
    duplicate.response.send_message.assert_awaited_once_with(
        "이미 투표했습니다.", ephemeral=True
    )
    advance.assert_not_awaited()


def test_two_thirds_vote_advances_to_next_scene(monkeypatch):
    advance = AsyncMock(return_value=True)
    monkeypatch.setattr("bot.cogs.narration.advance_narration_position", advance)
    view = _view()
    asyncio.run(view.advance.callback(_make_interaction(user_id=1)))
    interaction = _make_interaction(user_id=2)

    asyncio.run(view.advance.callback(interaction))

    advance.assert_awaited_once_with("pool", 9, 0, 0, 1, 0)
    _, kwargs = interaction.response.edit_message.call_args
    assert kwargs["embed"].description == "문장2"
    assert isinstance(kwargs["view"], NarrationView)


def test_one_keeper_vote_advances_when_no_pcs_participate(monkeypatch):
    advance = AsyncMock(return_value=True)
    monkeypatch.setattr("bot.cogs.narration.advance_narration_position", advance)
    view = _view({1})
    interaction = _make_interaction(user_id=1)

    asyncio.run(view.advance.callback(interaction))

    advance.assert_awaited_once_with("pool", 9, 0, 0, 1, 0)
    interaction.response.edit_message.assert_awaited_once()


def test_stale_narration_session_is_closed(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.narration.advance_narration_position", AsyncMock(return_value=False)
    )
    view = _view({1})
    interaction = _make_interaction(user_id=1)

    asyncio.run(view.advance.callback(interaction))

    interaction.response.edit_message.assert_awaited_once_with(
        content="다른 낭독 진행에서 이미 장면이 이동했습니다.", embed=None, view=None
    )


def test_last_line_marks_scenario_complete(monkeypatch):
    advance = AsyncMock(return_value=True)
    monkeypatch.setattr("bot.cogs.narration.advance_narration_position", advance)
    view = NarrationView(
        pool="pool",
        scenario_id=9,
        structure=[{"part": "제1부", "scene": "마지막 장면", "lines": ["끝"]}],
        scene_index=0,
        line_index=0,
        eligible_user_ids={1},
    )
    interaction = _make_interaction(user_id=1)

    asyncio.run(view.advance.callback(interaction))

    advance.assert_awaited_once_with("pool", 9, 0, 0, 1, 0)
    interaction.response.edit_message.assert_awaited_once_with(
        content="낭독이 완료되었습니다.", embed=None, view=None
    )
