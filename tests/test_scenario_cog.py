import asyncio
import threading
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.scenario import ScenarioCog, _extract_doc_id


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


def test_extract_doc_id_from_share_link():
    url = "https://docs.google.com/document/d/1QDAwKMpCwDQTw8VVdYWeE-ePzm6KTyCvWzM41Oh6h4I/edit?usp=sharing"
    assert _extract_doc_id(url) == "1QDAwKMpCwDQTw8VVdYWeE-ePzm6KTyCvWzM41Oh6h4I"


def test_extract_doc_id_returns_none_for_non_docs_url():
    assert _extract_doc_id("https://example.com") is None


def test_register_rejects_non_google_docs_link(monkeypatch):
    cog = ScenarioCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.register.callback(cog, interaction, "제목", "https://example.com"))

    interaction.response.send_message.assert_awaited_once_with(
        "구글독스 문서 링크가 아닙니다.", ephemeral=True
    )


def test_register_rejects_blank_title_before_fetch(monkeypatch):
    fetch_mock = AsyncMock()
    monkeypatch.setattr("bot.cogs.scenario.fetch_google_doc", fetch_mock)
    cog = ScenarioCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(
        cog.register.callback(
            cog, interaction, "  ", "https://docs.google.com/document/d/abc123/edit"
        )
    )

    fetch_mock.assert_not_awaited()
    interaction.response.send_message.assert_awaited_once_with(
        "시나리오 제목을 입력해주세요.", ephemeral=True
    )


def test_register_parses_and_stores_on_success(monkeypatch):
    monkeypatch.setattr("bot.cogs.scenario.fetch_google_doc", AsyncMock(return_value="<html></html>"))
    parse_threads = []

    def parse(html):
        parse_threads.append(threading.get_ident())
        return [{"part": "제1부", "scene": "장면 1", "lines": ["문장1"]}]

    monkeypatch.setattr("bot.cogs.scenario.parse_scenario_html", parse)
    create_mock = AsyncMock(return_value=1)
    monkeypatch.setattr("bot.cogs.scenario.create_scenario", create_mock)
    cog = ScenarioCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(
        cog.register.callback(
            cog, interaction, " 마지막 상영 ", "https://docs.google.com/document/d/abc123/edit"
        )
    )

    interaction.response.defer.assert_awaited_once()
    create_mock.assert_awaited_once()
    assert create_mock.await_args.args[2] == "마지막 상영"
    assert parse_threads[0] != threading.get_ident()
    interaction.followup.send.assert_awaited_once_with("'마지막 상영' 시나리오를 등록했습니다. (장면 1개)")


def test_register_reports_when_no_narration_found(monkeypatch):
    monkeypatch.setattr("bot.cogs.scenario.fetch_google_doc", AsyncMock(return_value="<html></html>"))
    monkeypatch.setattr("bot.cogs.scenario.parse_scenario_html", lambda html: [])
    cog = ScenarioCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(
        cog.register.callback(
            cog, interaction, "빈문서", "https://docs.google.com/document/d/abc123/edit"
        )
    )

    interaction.followup.send.assert_awaited_once_with(
        "문서에서 Keeper 낭독 구간을 찾지 못했습니다.", ephemeral=True
    )


def test_start_rejects_non_keeper(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.scenario.get_scenario_by_title",
        AsyncMock(return_value={"keeper_user_id": 999, "id": 1}),
    )
    cog = ScenarioCog(bot=_make_bot())
    interaction = _make_interaction(user_id=100)

    asyncio.run(cog.start.callback(cog, interaction, "시나리오"))

    interaction.response.send_message.assert_awaited_once_with(
        "이 시나리오의 키퍼만 시작할 수 있습니다.", ephemeral=True
    )


def test_start_binds_channel_for_keeper(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.scenario.get_scenario_by_title",
        AsyncMock(return_value={"keeper_user_id": 100, "id": 1}),
    )
    bind_mock = AsyncMock(return_value=True)
    monkeypatch.setattr("bot.cogs.scenario.bind_scenario_channel", bind_mock)
    cog = ScenarioCog(bot=_make_bot())
    interaction = _make_interaction(user_id=100)

    asyncio.run(cog.start.callback(cog, interaction, "시나리오"))

    bind_mock.assert_awaited_once()
    interaction.response.send_message.assert_awaited_once_with(
        "이 채널을 '시나리오' 시나리오에 배정했습니다."
    )


def test_start_reports_when_channel_taken(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.scenario.get_scenario_by_title",
        AsyncMock(return_value={"keeper_user_id": 100, "id": 1}),
    )
    monkeypatch.setattr(
        "bot.cogs.scenario.bind_scenario_channel", AsyncMock(return_value=False)
    )
    cog = ScenarioCog(bot=_make_bot())
    interaction = _make_interaction(user_id=100)

    asyncio.run(cog.start.callback(cog, interaction, "시나리오"))

    interaction.response.send_message.assert_awaited_once_with(
        "이 채널에는 이미 다른 시나리오가 배정돼 있습니다.", ephemeral=True
    )


def test_join_adds_registered_pc_to_channel_scenario(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.scenario.get_scenario_by_channel",
        AsyncMock(return_value={"id": 7}),
    )
    monkeypatch.setattr(
        "bot.cogs.scenario.get_pc_character",
        AsyncMock(return_value={"id": 42, "name": "탐사자"}),
    )
    join_mock = AsyncMock()
    monkeypatch.setattr("bot.cogs.scenario.join_scenario", join_mock)
    cog = ScenarioCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.join.callback(cog, interaction))

    join_mock.assert_awaited_once_with(cog.pool, 7, 42)
    interaction.response.send_message.assert_awaited_once_with(
        "탐사자가 시나리오에 참가했습니다."
    )


def test_join_rejects_unregistered_pc(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.scenario.get_scenario_by_channel",
        AsyncMock(return_value={"id": 7}),
    )
    monkeypatch.setattr(
        "bot.cogs.scenario.get_pc_character", AsyncMock(return_value=None)
    )
    join_mock = AsyncMock()
    monkeypatch.setattr("bot.cogs.scenario.join_scenario", join_mock)
    cog = ScenarioCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.join.callback(cog, interaction))

    join_mock.assert_not_awaited()
    interaction.response.send_message.assert_awaited_once_with(
        "등록된 PC 캐릭터가 없습니다.", ephemeral=True
    )


def test_info_reports_when_channel_unbound(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.scenario.get_scenario_by_channel", AsyncMock(return_value=None)
    )
    cog = ScenarioCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.info.callback(cog, interaction))

    interaction.response.send_message.assert_awaited_once_with(
        "이 채널에 배정된 시나리오가 없습니다.", ephemeral=True
    )
