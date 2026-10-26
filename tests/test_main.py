import asyncio
import socket
import re
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock

import aiohttp
import pytest

import bot.main as main_module


def test_main_raises_systemexit_without_token(monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    with pytest.raises(SystemExit):
        main_module.main()


def test_main_starts_without_database_path_or_gemini_key(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "fake-token-for-test")
    monkeypatch.delenv("DATABASE_PATH", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    run = []
    monkeypatch.setattr(main_module.bot, "run", run.append)

    main_module.main()

    assert run == ["fake-token-for-test"]


def test_start_web_server_noop_without_port(monkeypatch):
    monkeypatch.delenv("PORT", raising=False)
    bot = main_module.CoCBot()
    asyncio.run(bot._start_web_server())
    assert bot._web_runner is None


def test_start_web_server_responds_200(monkeypatch):
    with socket.socket() as s:
        s.bind(("localhost", 0))
        free_port = s.getsockname()[1]
    monkeypatch.setenv("PORT", str(free_port))

    async def _body():
        bot = main_module.CoCBot()
        await bot._start_web_server()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://localhost:{free_port}/") as resp:
                    assert resp.status == 200
        finally:
            await bot._web_runner.cleanup()

    asyncio.run(_body())


class _FakeResponse:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeSession:
    def __init__(self):
        self.requested_url = None

    def get(self, url):
        self.requested_url = url
        return _FakeResponse()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def test_self_ping_requests_external_url(monkeypatch):
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://coc-bot.onrender.com")
    fake_session = _FakeSession()
    monkeypatch.setattr(main_module.aiohttp, "ClientSession", lambda: fake_session)

    asyncio.run(main_module.CoCBot._self_ping.coro(None))

    assert fake_session.requested_url == "https://coc-bot.onrender.com"


def test_self_ping_swallows_client_error(monkeypatch):
    class _FailingSession:
        def get(self, url):
            raise main_module.aiohttp.ClientError("boom")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://coc-bot.onrender.com")
    monkeypatch.setattr(main_module.aiohttp, "ClientSession", lambda: _FailingSession())

    asyncio.run(main_module.CoCBot._self_ping.coro(None))  # must not raise


def test_shutdown_attempts_discord_and_database_cleanup_when_web_cleanup_fails(monkeypatch, caplog):
    from discord.ext import commands

    bot = main_module.CoCBot()
    web_cleanup = AsyncMock(side_effect=RuntimeError("secret web details"))
    db_close = AsyncMock()
    discord_close = AsyncMock()
    bot._web_runner = MagicMock(cleanup=web_cleanup)
    bot.pool = MagicMock(close=db_close)
    monkeypatch.setattr(main_module.CoCBot._self_ping, "cancel", Mock())
    monkeypatch.setattr(commands.Bot, "close", discord_close)

    with pytest.raises(RuntimeError, match="web shutdown failed") as exc_info:
        asyncio.run(bot.close())

    web_cleanup.assert_awaited_once()
    db_close.assert_awaited_once()
    discord_close.assert_awaited_once()
    assert "web" in caplog.text
    assert "secret web details" not in caplog.text
    assert "secret web details" not in str(exc_info.value)
    assert "duration_ms=" in caplog.text


def test_command_tree_records_receipt_without_command_arguments(monkeypatch, caplog):
    caplog.set_level("INFO", logger="coc-bot")
    interaction = SimpleNamespace(
        id=12345,
        command=SimpleNamespace(qualified_name="행동"),
        data={"options": [{"value": "비밀 지문"}]},
    )

    result = asyncio.run(main_module.bot.tree.interaction_check(interaction))

    assert result is True
    assert isinstance(interaction._coc_started_at, float)
    assert "12345" in caplog.text and "행동" in caplog.text
    assert "비밀 지문" not in caplog.text


def test_completion_log_has_duration_and_acknowledgement_without_arguments(monkeypatch, caplog):
    caplog.set_level("INFO", logger="coc-bot")
    interaction = SimpleNamespace(
        id=67890,
        command=SimpleNamespace(qualified_name="판정"),
        response=SimpleNamespace(is_done=lambda: True),
        _coc_started_at=time.monotonic() - 0.2,
        data={"options": [{"value": "민감한 입력"}]},
    )

    asyncio.run(main_module.on_app_command_completion(interaction, interaction.command))

    duration = re.search(r"command_duration_ms=(\d+)", caplog.text)
    assert "67890" in caplog.text and duration and int(duration.group(1)) >= 100
    assert "acknowledged_at_completion=True" in caplog.text
    assert "민감한 입력" not in caplog.text


def test_app_command_error_logs_correlation_without_exception_text(caplog):
    from discord import app_commands

    caplog.set_level("INFO", logger="coc-bot")
    interaction = SimpleNamespace(
        id=24680,
        command=SimpleNamespace(qualified_name="시나리오조회"),
        response=SimpleNamespace(is_done=lambda: True),
        followup=AsyncMock(),
        _coc_started_at=main_module.time.monotonic() - 0.01,
    )

    asyncio.run(main_module.on_app_command_error(
        interaction, app_commands.AppCommandError("private input and token")
    ))

    assert "24680" in caplog.text
    assert "acknowledged_at_completion=True" in caplog.text
    assert "failed" in caplog.text
    assert "private input and token" not in caplog.text
    interaction.followup.send.assert_awaited_once()
