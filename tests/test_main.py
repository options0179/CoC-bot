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
