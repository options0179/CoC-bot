import asyncio
import http.client
import socket

import pytest

import bot.main as main_module


def test_main_raises_systemexit_without_token(monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    with pytest.raises(SystemExit):
        main_module.main()


def test_main_raises_systemexit_without_database_url(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "fake-token-for-test")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(SystemExit):
        main_module.main()


def test_main_raises_systemexit_without_gemini_key(monkeypatch):
    monkeypatch.setenv("DISCORD_TOKEN", "fake-token-for-test")
    monkeypatch.setenv("DATABASE_URL", "postgres://fake-url-for-test")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        main_module.main()


def test_run_health_check_server_noop_without_port(monkeypatch):
    monkeypatch.delenv("PORT", raising=False)
    main_module._run_health_check_server()  # must not raise or bind anything


def test_run_health_check_server_responds_200(monkeypatch):
    with socket.socket() as s:
        s.bind(("localhost", 0))
        free_port = s.getsockname()[1]
    monkeypatch.setenv("PORT", str(free_port))
    main_module._run_health_check_server()
    conn = http.client.HTTPConnection("localhost", free_port, timeout=2)
    conn.request("GET", "/")
    resp = conn.getresponse()
    assert resp.status == 200


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
