import asyncio
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.character import CharacterCog


def _make_interaction(guild_id=1, user_id=100):
    interaction = MagicMock()
    interaction.response = AsyncMock()
    interaction.guild_id = guild_id
    interaction.user = MagicMock(id=user_id)
    return interaction


def _make_bot():
    bot = MagicMock()
    bot.pool = MagicMock()
    return bot


def test_open_window_succeeds(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.character.open_registration", AsyncMock(return_value=True)
    )
    cog = CharacterCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.open_window.callback(cog, interaction))

    interaction.response.send_message.assert_awaited_once_with("캐릭터 등록창을 열었습니다.")


def test_open_window_rejected_when_already_open(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.character.open_registration", AsyncMock(return_value=False)
    )
    cog = CharacterCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.open_window.callback(cog, interaction))

    interaction.response.send_message.assert_awaited_once_with(
        "이미 다른 사람이 등록창을 열어뒀습니다.", ephemeral=True
    )


def test_close_window_succeeds_for_opener(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.character.close_registration", AsyncMock(return_value=True)
    )
    cog = CharacterCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.close_window.callback(cog, interaction))

    interaction.response.send_message.assert_awaited_once_with("캐릭터 등록창을 닫았습니다.")


def test_close_window_rejected_for_non_opener(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.character.close_registration", AsyncMock(return_value=False)
    )
    cog = CharacterCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.close_window.callback(cog, interaction))

    interaction.response.send_message.assert_awaited_once_with(
        "본인이 연 등록창만 닫을 수 있습니다.", ephemeral=True
    )
