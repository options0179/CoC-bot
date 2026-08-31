import pytest

import bot.main as main_module


def test_main_raises_systemexit_without_token(monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    with pytest.raises(SystemExit):
        main_module.main()
