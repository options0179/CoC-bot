import asyncio
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.narration import NarrationView


def _make_interaction(user_id):
    interaction = MagicMock()
    interaction.response = AsyncMock()
    interaction.user = MagicMock(id=user_id)
    return interaction


def test_non_participant_vote_rejected():
    view = NarrationView(roster_user_ids={1, 2}, keeper_user_id=99)
    interaction = _make_interaction(user_id=123)

    asyncio.run(view.advance.callback(interaction))

    interaction.response.send_message.assert_awaited_once_with(
        "이 시나리오의 참가자만 투표할 수 있습니다.", ephemeral=True
    )
    assert view.advance.disabled is False


def test_duplicate_vote_rejected():
    view = NarrationView(roster_user_ids={1, 2, 3}, keeper_user_id=99)
    interaction = _make_interaction(user_id=1)

    asyncio.run(view.advance.callback(interaction))
    asyncio.run(view.advance.callback(interaction))

    assert interaction.response.send_message.await_count == 2
    _, kwargs = interaction.response.send_message.call_args
    assert kwargs["ephemeral"] is True
    assert view.votes == {1}


def test_threshold_not_reached_below_two_thirds():
    # roster 3명 + 키퍼 1명 = 분모 4, 2/3 = 2.67 -> 3표 필요
    view = NarrationView(roster_user_ids={1, 2, 3}, keeper_user_id=99)
    for uid in (1, 2):
        interaction = _make_interaction(user_id=uid)
        asyncio.run(view.advance.callback(interaction))
    assert view.advance.disabled is False


def test_threshold_reached_stops_view():
    view = NarrationView(roster_user_ids={1, 2, 3}, keeper_user_id=99)
    for uid in (1, 2, 3):
        interaction = _make_interaction(user_id=uid)
        asyncio.run(view.advance.callback(interaction))
    assert view.advance.disabled is True


def test_keeper_vote_counts_toward_threshold():
    # roster 1명 + 키퍼 1명 = 분모 2, 2/3 = 1.33 -> 2표 필요, 키퍼 포함
    view = NarrationView(roster_user_ids={1}, keeper_user_id=99)
    asyncio.run(view.advance.callback(_make_interaction(user_id=1)))
    assert view.advance.disabled is False
    asyncio.run(view.advance.callback(_make_interaction(user_id=99)))
    assert view.advance.disabled is True
