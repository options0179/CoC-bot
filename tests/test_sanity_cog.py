import asyncio
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.sanity import SanityCog
from dice import SanityResult


def _make_interaction():
    interaction = MagicMock()
    interaction.response = AsyncMock()
    return interaction


def test_sanity_command_sends_embed(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.sanity.sanity_check",
        lambda current_san, formula: SanityResult(
            roll=20, current_san=current_san, success=True, loss=1, remaining_san=current_san - 1
        ),
    )
    cog = SanityCog(bot=MagicMock())
    interaction = _make_interaction()

    asyncio.run(cog.sanity.callback(cog, interaction, 현재san=50, 손실식="1/1d4+1"))

    interaction.response.send_message.assert_awaited_once()
    _, kwargs = interaction.response.send_message.call_args
    assert kwargs["embed"] is not None
