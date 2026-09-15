import asyncio
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.character import CharacterCog, _build_registration_url, _extract_sheet_id

_SHEET_URL = "https://docs.google.com/spreadsheets/d/abc123/edit?usp=sharing"


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


class _FakeResponse:
    status = 200

    async def read(self):
        return b"fake-bytes"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeSession:
    def get(self, url):
        return _FakeResponse()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def test_extract_sheet_id_from_share_link():
    assert _extract_sheet_id(_SHEET_URL) == "abc123"


def test_extract_sheet_id_returns_none_for_non_sheets_url():
    assert _extract_sheet_id("https://example.com") is None


def test_build_registration_url_uses_render_external_url(monkeypatch):
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://coc-bot.onrender.com")
    assert _build_registration_url("abc") == "https://coc-bot.onrender.com/register/abc"


def test_build_registration_url_falls_back_to_localhost(monkeypatch):
    monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)
    monkeypatch.setenv("PORT", "9000")
    assert _build_registration_url("abc") == "http://localhost:9000/register/abc"


def test_register_issues_token_link_when_no_link_given(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.character.is_registration_open", AsyncMock(return_value=True)
    )
    token_mock = AsyncMock(return_value="tok123")
    monkeypatch.setattr("bot.cogs.character.create_registration_token", token_mock)
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://coc-bot.onrender.com")
    cog = CharacterCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.register.callback(cog, interaction, None))

    token_mock.assert_awaited_once_with(cog.pool, interaction.guild_id, interaction.user.id, role="PC")
    interaction.response.send_message.assert_awaited_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "https://coc-bot.onrender.com/register/tok123" in args[0]
    assert kwargs["ephemeral"] is True
    interaction.response.defer.assert_not_awaited()


def test_register_token_branch_rejected_when_window_closed(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.character.is_registration_open", AsyncMock(return_value=False)
    )
    cog = CharacterCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.register.callback(cog, interaction, None))

    interaction.response.send_message.assert_awaited_once_with(
        "지금은 등록 기간이 아닙니다.", ephemeral=True
    )


def test_register_rejected_for_non_sheet_link(monkeypatch):
    cog = CharacterCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.register.callback(cog, interaction, "https://example.com"))

    interaction.response.send_message.assert_awaited_once_with(
        "구글 스프레드시트 링크가 아닙니다.", ephemeral=True
    )
    interaction.response.defer.assert_not_awaited()


def test_register_rejected_when_window_closed(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.character.is_registration_open", AsyncMock(return_value=False)
    )
    cog = CharacterCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.register.callback(cog, interaction, _SHEET_URL))

    interaction.response.defer.assert_awaited_once()
    interaction.followup.send.assert_awaited_once_with(
        "지금은 등록 기간이 아닙니다.", ephemeral=True
    )


def test_register_parses_and_stores_on_success(monkeypatch):
    monkeypatch.setattr("bot.cogs.character.aiohttp.ClientSession", lambda: _FakeSession())
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

    asyncio.run(cog.register.callback(cog, interaction, _SHEET_URL))

    interaction.response.defer.assert_awaited_once()
    upsert_mock.assert_awaited_once()
    interaction.followup.send.assert_awaited_once_with("탐사자 캐릭터를 등록했습니다.")


def test_register_reports_fetch_error(monkeypatch):
    class _FailingResponse(_FakeResponse):
        status = 404

    class _FailingSession(_FakeSession):
        def get(self, url):
            return _FailingResponse()

    monkeypatch.setattr("bot.cogs.character.aiohttp.ClientSession", lambda: _FailingSession())
    monkeypatch.setattr(
        "bot.cogs.character.is_registration_open", AsyncMock(return_value=True)
    )
    cog = CharacterCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.register.callback(cog, interaction, _SHEET_URL))

    interaction.followup.send.assert_awaited_once_with(
        "시트를 가져올 수 없습니다. 링크 공개 설정을 확인하세요.", ephemeral=True
    )


def test_register_reports_parse_error(monkeypatch):
    monkeypatch.setattr("bot.cogs.character.aiohttp.ClientSession", lambda: _FakeSession())
    monkeypatch.setattr(
        "bot.cogs.character.is_registration_open", AsyncMock(return_value=True)
    )

    def _raise(file_bytes):
        raise ValueError("'이름' 항목을 시트에서 찾을 수 없습니다.")

    monkeypatch.setattr("bot.cogs.character.parse_character_sheet", _raise)
    cog = CharacterCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.register.callback(cog, interaction, _SHEET_URL))

    interaction.response.defer.assert_awaited_once()
    interaction.followup.send.assert_awaited_once_with(
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


class _FakeRole:
    def __init__(self, value):
        self.value = value


def test_register_scenario_character_rejects_non_keeper(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.character.get_scenario_by_title",
        AsyncMock(return_value={"id": 1, "keeper_user_id": 999}),
    )
    cog = CharacterCog(bot=_make_bot())
    interaction = _make_interaction(user_id=100)

    asyncio.run(
        cog.register_scenario_character.callback(
            cog, interaction, "시나리오", _FakeRole("NPC"), _SHEET_URL
        )
    )

    interaction.response.send_message.assert_awaited_once_with(
        "이 시나리오의 키퍼만 등록할 수 있습니다.", ephemeral=True
    )


def test_register_scenario_character_token_branch_rejects_non_keeper(monkeypatch):
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
            cog, interaction, "시나리오", _FakeRole("NPC"), None
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
            cog, interaction, "없음", _FakeRole("NPC"), _SHEET_URL
        )
    )

    interaction.response.send_message.assert_awaited_once_with(
        "등록된 시나리오가 아닙니다.", ephemeral=True
    )


def test_register_scenario_character_rejects_non_sheet_link(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.character.get_scenario_by_title",
        AsyncMock(return_value={"id": 7, "keeper_user_id": 100}),
    )
    cog = CharacterCog(bot=_make_bot())
    interaction = _make_interaction(user_id=100)

    asyncio.run(
        cog.register_scenario_character.callback(
            cog, interaction, "시나리오", _FakeRole("NPC"), "https://example.com"
        )
    )

    interaction.response.send_message.assert_awaited_once_with(
        "구글 스프레드시트 링크가 아닙니다.", ephemeral=True
    )


def test_register_scenario_character_issues_token_link_when_no_link_given(monkeypatch):
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
            cog, interaction, "시나리오", _FakeRole("NPC"), None
        )
    )

    token_mock.assert_awaited_once_with(
        cog.pool, interaction.guild_id, interaction.user.id, role="NPC", scenario_id=7
    )
    interaction.response.send_message.assert_awaited_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "https://coc-bot.onrender.com/register/tok456" in args[0]
    assert kwargs["ephemeral"] is True
    interaction.response.defer.assert_not_awaited()


def test_register_scenario_character_stores_npc_for_keeper(monkeypatch):
    monkeypatch.setattr("bot.cogs.character.aiohttp.ClientSession", lambda: _FakeSession())
    monkeypatch.setattr(
        "bot.cogs.character.get_scenario_by_title",
        AsyncMock(return_value={"id": 7, "keeper_user_id": 100}),
    )
    monkeypatch.setattr(
        "bot.cogs.character.parse_character_sheet",
        lambda file_bytes: {"name": "관리인", "skills": {}},
    )
    upsert_mock = AsyncMock()
    monkeypatch.setattr("bot.cogs.character.upsert_character", upsert_mock)
    cog = CharacterCog(bot=_make_bot())
    interaction = _make_interaction(user_id=100)

    asyncio.run(
        cog.register_scenario_character.callback(
            cog, interaction, "시나리오", _FakeRole("NPC"), _SHEET_URL
        )
    )

    upsert_mock.assert_awaited_once_with(
        cog.pool, interaction.guild_id, interaction.user.id,
        {"name": "관리인", "skills": {}}, role="NPC", scenario_id=7,
    )
    interaction.followup.send.assert_awaited_once_with("관리인 (NPC)을(를) 등록했습니다.")
