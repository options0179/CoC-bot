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


def _make_character(**overrides):
    base = {
        "san_current": 50,
        "is_retired": False,
        "temp_insanity": False,
        "indefinite_insanity": False,
    }
    base.update(overrides)
    return base


def _patch_sanity_result(monkeypatch, loss, remaining_san=None):
    monkeypatch.setattr(
        "bot.cogs.sanity.sanity_check",
        lambda current_san, formula: SanityResult(
            roll=80,
            current_san=current_san,
            success=False,
            loss=loss,
            remaining_san=current_san - loss if remaining_san is None else remaining_san,
        ),
    )


def test_sanity_rejects_when_no_character(monkeypatch):
    monkeypatch.setattr("bot.cogs.sanity.get_pc_character", AsyncMock(return_value=None))
    cog = SanityCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.sanity.callback(cog, interaction, 손실식="1/1d4+1"))

    interaction.response.send_message.assert_awaited_once_with(
        "등록된 캐릭터가 없습니다.", ephemeral=True
    )


def test_sanity_rejects_when_already_retired(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.sanity.get_pc_character",
        AsyncMock(return_value=_make_character(is_retired=True)),
    )
    cog = SanityCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.sanity.callback(cog, interaction, 손실식="1/1d4+1"))

    interaction.response.send_message.assert_awaited_once_with(
        "이미 영구적 광기로 퇴장한 캐릭터입니다.", ephemeral=True
    )


def test_sanity_rolls_using_db_san_and_persists_result(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.sanity.get_pc_character",
        AsyncMock(return_value=_make_character(san_current=50)),
    )
    monkeypatch.setattr(
        "bot.cogs.sanity.sanity_check",
        lambda current_san, formula: SanityResult(
            roll=20, current_san=current_san, success=True, loss=1, remaining_san=current_san - 1
        ),
    )
    update_mock = AsyncMock()
    monkeypatch.setattr("bot.cogs.sanity.update_san_current", update_mock)
    cog = SanityCog(bot=_make_bot())
    interaction = _make_interaction(guild_id=1, user_id=100)

    asyncio.run(cog.sanity.callback(cog, interaction, 손실식="1/1d4+1"))

    update_mock.assert_awaited_once_with(
        cog.pool, 1, 100, 49, temp_insanity=False, indefinite_insanity=False
    )
    interaction.response.send_message.assert_awaited_once()
    _, kwargs = interaction.response.send_message.call_args
    assert kwargs["embed"] is not None


def test_sanity_warns_on_loss_of_5_or_more(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.sanity.get_pc_character",
        AsyncMock(return_value=_make_character(san_current=50)),
    )
    monkeypatch.setattr(
        "bot.cogs.sanity.sanity_check",
        lambda current_san, formula: SanityResult(
            roll=80, current_san=current_san, success=False, loss=5, remaining_san=current_san - 5
        ),
    )
    monkeypatch.setattr("bot.cogs.sanity.update_san_current", AsyncMock())
    embed_mock = MagicMock()
    monkeypatch.setattr("bot.cogs.sanity.sanity_embed", embed_mock)
    cog = SanityCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.sanity.callback(cog, interaction, 손실식="1/1d4+4"))

    _, kwargs = embed_mock.call_args
    warnings = embed_mock.call_args[0][1]
    assert any("일시적 광기" in w for w in warnings)


def test_sanity_warns_and_retires_on_reaching_zero(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.sanity.get_pc_character",
        AsyncMock(return_value=_make_character(san_current=3)),
    )
    monkeypatch.setattr(
        "bot.cogs.sanity.sanity_check",
        lambda current_san, formula: SanityResult(
            roll=80, current_san=current_san, success=False, loss=3, remaining_san=0
        ),
    )
    update_mock = AsyncMock()
    monkeypatch.setattr("bot.cogs.sanity.update_san_current", update_mock)
    embed_mock = MagicMock()
    monkeypatch.setattr("bot.cogs.sanity.sanity_embed", embed_mock)
    cog = SanityCog(bot=_make_bot())
    interaction = _make_interaction(guild_id=1, user_id=100)

    asyncio.run(cog.sanity.callback(cog, interaction, 손실식="1/3"))

    update_mock.assert_awaited_once_with(
        cog.pool, 1, 100, 0, temp_insanity=False, indefinite_insanity=True
    )
    warnings = embed_mock.call_args[0][1]
    assert any("퇴장" in w for w in warnings)


def test_sanity_persists_temp_insanity_and_keeps_warning(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.sanity.get_pc_character",
        AsyncMock(return_value=_make_character(san_current=50)),
    )
    _patch_sanity_result(monkeypatch, loss=5)
    update_mock = AsyncMock()
    monkeypatch.setattr("bot.cogs.sanity.update_san_current", update_mock)
    embed_mock = MagicMock()
    monkeypatch.setattr("bot.cogs.sanity.sanity_embed", embed_mock)
    cog = SanityCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.sanity.callback(cog, interaction, 손실식="1/1d4+4"))

    _, update_kwargs = update_mock.call_args
    assert update_kwargs["temp_insanity"] is True
    assert update_kwargs["indefinite_insanity"] is False
    warnings = embed_mock.call_args[0][1]
    assert any("일시적 광기" in w for w in warnings)


def test_sanity_persists_indefinite_insanity_and_keeps_warning(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.sanity.get_pc_character",
        AsyncMock(return_value=_make_character(san_current=50)),
    )
    _patch_sanity_result(monkeypatch, loss=10)
    update_mock = AsyncMock()
    monkeypatch.setattr("bot.cogs.sanity.update_san_current", update_mock)
    embed_mock = MagicMock()
    monkeypatch.setattr("bot.cogs.sanity.sanity_embed", embed_mock)
    cog = SanityCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.sanity.callback(cog, interaction, 손실식="1/10"))

    _, update_kwargs = update_mock.call_args
    assert update_kwargs["indefinite_insanity"] is True
    warnings = embed_mock.call_args[0][1]
    assert any("부정형 광기" in w for w in warnings)


def test_sanity_leaves_flags_false_on_small_loss(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.sanity.get_pc_character",
        AsyncMock(return_value=_make_character(san_current=50)),
    )
    _patch_sanity_result(monkeypatch, loss=1)
    update_mock = AsyncMock()
    monkeypatch.setattr("bot.cogs.sanity.update_san_current", update_mock)
    cog = SanityCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.sanity.callback(cog, interaction, 손실식="1/1"))

    _, update_kwargs = update_mock.call_args
    assert update_kwargs["temp_insanity"] is False
    assert update_kwargs["indefinite_insanity"] is False


def test_sanity_embed_receives_already_latched_status(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.sanity.get_pc_character",
        AsyncMock(return_value=_make_character(san_current=50, temp_insanity=True)),
    )
    _patch_sanity_result(monkeypatch, loss=1)
    monkeypatch.setattr("bot.cogs.sanity.update_san_current", AsyncMock())
    embed_mock = MagicMock()
    monkeypatch.setattr("bot.cogs.sanity.sanity_embed", embed_mock)
    cog = SanityCog(bot=_make_bot())
    interaction = _make_interaction()

    asyncio.run(cog.sanity.callback(cog, interaction, 손실식="1/1"))

    statuses = embed_mock.call_args.kwargs["statuses"]
    assert "일시적 광기" in statuses
