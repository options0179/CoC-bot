import asyncio
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.narration import NarrationView


def _make_interaction(user_id):
    interaction = MagicMock()
    interaction.response = AsyncMock()
    interaction.user = MagicMock(id=user_id)
    return interaction


def test_non_keeper_advance_rejected():
    view = NarrationView(keeper_user_id=99)
    interaction = _make_interaction(user_id=123)

    asyncio.run(view.advance.callback(interaction))

    interaction.response.send_message.assert_awaited_once_with(
        "키퍼만 진행할 수 있습니다.", ephemeral=True
    )
    assert view.advance.disabled is False


def test_keeper_advance_stops_view():
    view = NarrationView(keeper_user_id=99)
    interaction = _make_interaction(user_id=99)

    asyncio.run(view.advance.callback(interaction))

    assert view.advance.disabled is True
