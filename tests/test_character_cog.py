import asyncio
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.character import CharacterCog, _build_registration_url


def _make_interaction(guild_id=1, user_id=100):
    interaction = MagicMock()
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.guild_id = guild_id
    interaction.user = MagicMock(id=user_id)
    return interaction


def _make_bot():
    bot = MagicMock()
    bot.pool = MagicMock()
    return bot


def test_build_registration_url_uses_render_external_url(monkeypatch):
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://coc-bot.onrender.com")
    assert _build_registration_url("abc") == "https://coc-bot.onrender.com/register/abc"


def test_build_registration_url_falls_back_to_localhost(monkeypatch):
    monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)
    monkeypatch.setenv("PORT", "9000")
    assert _build_registration_url("abc") == "http://localhost:9000/register/abc"


def test_register_issues_token_link(monkeypatch):
    token_mock = AsyncMock(return_value="tok123")
    monkeypatch.setattr("bot.cogs.character.create_registration_token", token_mock)
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://coc-bot.onrender.com")
    cog = CharacterCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.register.callback(cog, interaction))

    token_mock.assert_awaited_once_with(cog.pool, interaction.guild_id, interaction.user.id, role="PC")
    interaction.response.send_message.assert_awaited_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "https://coc-bot.onrender.com/register/tok123" in args[0]
    assert kwargs["ephemeral"] is True


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


class _FakeRole:
    def __init__(self, value):
        self.value = value


def test_register_scenario_character_rejects_non_keeper(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.character.get_scenario_by_title",
        AsyncMock(return_value={"id": 1, "keeper_user_id": 999}),
    )
    token_mock = AsyncMock()
    monkeypatch.setattr("bot.cogs.character.create_registration_token", token_mock)
    cog = CharacterCog(bot=_make_bot())
    interaction = _make_interaction(user_id=100)

    asyncio.run(
        cog.register_scenario_character.callback(
            cog, interaction, "시나리오", _FakeRole("NPC")
        )
    )

    interaction.response.send_message.assert_awaited_once_with(
        "이 시나리오의 키퍼만 등록할 수 있습니다.", ephemeral=True
    )
    token_mock.assert_not_awaited()


def test_register_scenario_character_rejects_unknown_scenario(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.character.get_scenario_by_title", AsyncMock(return_value=None)
    )
    cog = CharacterCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(
        cog.register_scenario_character.callback(
            cog, interaction, "없음", _FakeRole("NPC")
        )
    )

    interaction.response.send_message.assert_awaited_once_with(
        "등록된 시나리오가 아닙니다.", ephemeral=True
    )


def test_register_scenario_character_issues_token_link(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.character.get_scenario_by_title",
        AsyncMock(return_value={"id": 7, "keeper_user_id": 100}),
    )
    token_mock = AsyncMock(return_value="tok456")
    monkeypatch.setattr("bot.cogs.character.create_registration_token", token_mock)
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://coc-bot.onrender.com")
    cog = CharacterCog(bot=_make_bot())
    interaction = _make_interaction(user_id=100)

    asyncio.run(
        cog.register_scenario_character.callback(
            cog, interaction, "시나리오", _FakeRole("NPC")
        )
    )

    token_mock.assert_awaited_once_with(
        cog.pool, interaction.guild_id, interaction.user.id, role="NPC", scenario_id=7
    )
    interaction.response.send_message.assert_awaited_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "https://coc-bot.onrender.com/register/tok456" in args[0]
    assert kwargs["ephemeral"] is True
