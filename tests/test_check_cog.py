import asyncio
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.check import CheckCog, PushView
from dice import CheckResult, SuccessLevel


def _make_interaction(user_id=7):
    interaction = MagicMock()
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    interaction.user = MagicMock(id=user_id)
    return interaction


def test_check_attaches_push_view_on_failure(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.check.roll_check",
        lambda skill, bonus=0, penalty=0: CheckResult(roll=90, skill=skill, level=SuccessLevel.FAIL),
    )
    cog = CheckCog(bot=MagicMock())
    interaction = _make_interaction(user_id=8)

    asyncio.run(cog.check.callback(cog, interaction, 스킬값=50, 보너스=0, 페널티=0))

    interaction.response.send_message.assert_awaited_once()
    _, kwargs = interaction.response.send_message.call_args
    assert isinstance(kwargs["view"], PushView)


def test_check_no_push_view_on_success(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.check.roll_check",
        lambda skill, bonus=0, penalty=0: CheckResult(roll=10, skill=skill, level=SuccessLevel.REGULAR),
    )
    cog = CheckCog(bot=MagicMock())
    interaction = _make_interaction()

    asyncio.run(cog.check.callback(cog, interaction, 스킬값=50, 보너스=0, 페널티=0))

    interaction.response.send_message.assert_awaited_once()
    _, kwargs = interaction.response.send_message.call_args
    assert "view" not in kwargs


def test_push_view_reroll_disables_button_and_sends_followup(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.check.roll_check",
        lambda skill, bonus=0, penalty=0: CheckResult(roll=5, skill=skill, level=SuccessLevel.EXTREME),
    )
    view = PushView(owner_user_id=7, skill=50, bonus=0, penalty=0)
    interaction = _make_interaction()

    # discord.py binds ui.button items to the view instance at construction
    # time, so the item's .callback takes only `interaction` — `self` and
    # `button` are already bound internally to this same item.
    asyncio.run(view.push.callback(interaction))

    assert view.pushed is True
    assert view.push.disabled is True
    interaction.response.edit_message.assert_awaited_once()
    interaction.followup.send.assert_awaited_once()


def test_push_view_second_click_is_noop(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.check.roll_check",
        lambda skill, bonus=0, penalty=0: CheckResult(roll=5, skill=skill, level=SuccessLevel.EXTREME),
    )
    view = PushView(owner_user_id=7, skill=50, bonus=0, penalty=0)
    view.pushed = True
    interaction = _make_interaction()

    asyncio.run(view.push.callback(interaction))

    interaction.response.send_message.assert_awaited_once_with("이미 푸시했습니다.", ephemeral=True)
    interaction.response.edit_message.assert_not_called()


def test_push_view_rejects_another_users_click():
    view = PushView(owner_user_id=7, skill=50, bonus=0, penalty=0)
    interaction = _make_interaction()
    interaction.user.id = 8

    asyncio.run(view.push.callback(interaction))

    interaction.response.send_message.assert_awaited_once_with(
        "이 판정을 실행한 사용자만 푸시할 수 있습니다.", ephemeral=True
    )
    assert view.pushed is False
