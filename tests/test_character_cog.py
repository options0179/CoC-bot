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


def _make_attachment(file_bytes: bytes = b"fake-bytes"):
    attachment = MagicMock()
    attachment.read = AsyncMock(return_value=file_bytes)
    return attachment


def test_register_rejected_when_window_closed(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.character.is_registration_open", AsyncMock(return_value=False)
    )
    cog = CharacterCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.register.callback(cog, interaction, _make_attachment()))

    interaction.response.send_message.assert_awaited_once_with(
        "지금은 등록 기간이 아닙니다.", ephemeral=True
    )


def test_register_parses_and_stores_on_success(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.character.is_registration_open", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        "bot.cogs.character.parse_character_sheet",
        lambda file_bytes: {"name": "탐사자", "skills": {}},
    )
    upsert_mock = AsyncMock()
    monkeypatch.setattr("bot.cogs.character.upsert_character", upsert_mock)
    cog = CharacterCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.register.callback(cog, interaction, _make_attachment()))

    upsert_mock.assert_awaited_once()
    interaction.response.send_message.assert_awaited_once_with("탐사자 캐릭터를 등록했습니다.")


def test_register_reports_parse_error(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.character.is_registration_open", AsyncMock(return_value=True)
    )

    def _raise(file_bytes):
        raise ValueError("'이름' 항목을 시트에서 찾을 수 없습니다.")

    monkeypatch.setattr("bot.cogs.character.parse_character_sheet", _raise)
    cog = CharacterCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.register.callback(cog, interaction, _make_attachment()))

    interaction.response.send_message.assert_awaited_once_with(
        "시트를 읽을 수 없습니다: '이름' 항목을 시트에서 찾을 수 없습니다.", ephemeral=True
    )


def test_lookup_reports_missing_character(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.character.get_character", AsyncMock(return_value=None)
    )
    cog = CharacterCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.lookup.callback(cog, interaction, None))

    interaction.response.send_message.assert_awaited_once_with(
        "등록된 캐릭터가 없습니다.", ephemeral=True
    )


def test_lookup_sends_embed_for_self_when_no_target_given(monkeypatch):
    character = {
        "name": "탐사자", "occupation": "사립탐정",
        "str": 50, "dex": 60, "pow": 55, "con": 65, "app": 45,
        "edu": 70, "siz": 50, "int": 80, "mov": 8, "skills": {},
    }
    monkeypatch.setattr(
        "bot.cogs.character.get_character", AsyncMock(return_value=character)
    )
    cog = CharacterCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.lookup.callback(cog, interaction, None))

    interaction.response.send_message.assert_awaited_once()
    _, kwargs = interaction.response.send_message.call_args
    assert kwargs["embed"].title == "탐사자"
