import asyncio
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.sanity import SanityCog
from dice import SanityResult


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


def _result(current_san=50, loss=1):
    return SanityResult(
        roll=20,
        current_san=current_san,
        success=True,
        loss=loss,
        remaining_san=max(0, current_san - loss),
    )


def test_sanity_rejects_when_no_character(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.sanity.resolve_sanity_check", AsyncMock(return_value=("missing", None))
    )
    cog = SanityCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.sanity.callback(cog, interaction, 손실식="1/1d4+1"))

    interaction.response.send_message.assert_awaited_once_with(
        "등록된 캐릭터가 없습니다.", ephemeral=True
    )


def test_sanity_rejects_when_already_retired(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.sanity.resolve_sanity_check", AsyncMock(return_value=("retired", None))
    )
    cog = SanityCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.sanity.callback(cog, interaction, 손실식="1/1d4+1"))

    interaction.response.send_message.assert_awaited_once_with(
        "이미 영구적 광기로 퇴장한 캐릭터입니다.", ephemeral=True
    )


def test_sanity_rejects_when_san_is_missing(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.sanity.resolve_sanity_check", AsyncMock(return_value=("incomplete", None))
    )
    cog = SanityCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.sanity.callback(cog, interaction, 손실식="1/1d4+1"))

    interaction.response.send_message.assert_awaited_once_with(
        "캐릭터의 SAN 값이 없습니다. 캐릭터 시트를 다시 등록해주세요.", ephemeral=True
    )


def test_sanity_uses_atomic_storage_operation(monkeypatch):
    resolve_mock = AsyncMock(return_value=("ok", _result()))
    monkeypatch.setattr("bot.cogs.sanity.resolve_sanity_check", resolve_mock)
    monkeypatch.setattr("bot.cogs.sanity.get_pc_character", AsyncMock(return_value={}))
    cog = SanityCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.sanity.callback(cog, interaction, 손실식="1/1d4+1"))

    resolve_mock.assert_awaited_once_with(cog.pool, 1, 100, "1/1d4+1")
    interaction.response.send_message.assert_awaited_once()
    _, kwargs = interaction.response.send_message.call_args
    assert kwargs["embed"] is not None


def test_sanity_warns_on_loss_of_5_or_more(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.sanity.resolve_sanity_check", AsyncMock(return_value=("ok", _result(loss=5)))
    )
    monkeypatch.setattr("bot.cogs.sanity.get_pc_character", AsyncMock(return_value={}))
    embed_mock = MagicMock()
    monkeypatch.setattr("bot.cogs.sanity.sanity_embed", embed_mock)
    cog = SanityCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.sanity.callback(cog, interaction, 손실식="1/1d4+4"))

    warnings = embed_mock.call_args[0][1]
    assert any("일시적 광기" in warning for warning in warnings)


def test_sanity_warns_when_san_reaches_zero(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.sanity.resolve_sanity_check",
        AsyncMock(return_value=("ok", _result(current_san=3, loss=3))),
    )
    monkeypatch.setattr("bot.cogs.sanity.get_pc_character", AsyncMock(return_value={}))
    embed_mock = MagicMock()
    monkeypatch.setattr("bot.cogs.sanity.sanity_embed", embed_mock)
    cog = SanityCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.sanity.callback(cog, interaction, 손실식="1/3"))

    warnings = embed_mock.call_args[0][1]
    assert any("퇴장" in warning for warning in warnings)
