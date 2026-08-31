import asyncio
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.opposed import OpposedCog
from dice import CheckResult, OpposedResult, SuccessLevel


def _make_interaction():
    interaction = MagicMock()
    interaction.response = AsyncMock()
    return interaction


def test_opposed_command_sends_embed(monkeypatch):
    a = CheckResult(roll=10, skill=60, level=SuccessLevel.EXTREME)
    b = CheckResult(roll=50, skill=40, level=SuccessLevel.REGULAR)
    monkeypatch.setattr(
        "bot.cogs.opposed.opposed_check",
        lambda skill_a, skill_b: OpposedResult(a=a, b=b, winner="a"),
    )
    cog = OpposedCog(bot=MagicMock())
    interaction = _make_interaction()

    asyncio.run(cog.opposed.callback(cog, interaction, 내스킬=60, 상대스킬=40))

    interaction.response.send_message.assert_awaited_once()
    _, kwargs = interaction.response.send_message.call_args
    assert kwargs["embed"] is not None
