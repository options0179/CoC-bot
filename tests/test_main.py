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
