from bot.embeds import check_embed, opposed_embed, sanity_embed
from dice import CheckResult, OpposedResult, SanityResult, SuccessLevel


def test_check_embed_shows_roll_and_level():
    result = CheckResult(roll=30, skill=60, level=SuccessLevel.REGULAR)
    embed = check_embed(result)
    assert "30" in embed.description
    assert "60" in embed.description
    assert embed.fields[0].value == "성공"


def test_check_embed_fumble_label():
    result = CheckResult(roll=99, skill=40, level=SuccessLevel.FUMBLE)
    embed = check_embed(result)
    assert embed.fields[0].value == "펌블"


def test_sanity_embed_shows_loss_and_remaining():
    result = SanityResult(roll=20, current_san=50, success=True, loss=1, remaining_san=49)
    embed = sanity_embed(result)
    values = [f.value for f in embed.fields]
    assert "성공" in values
    assert "-1" in values
    assert "49" in values


def test_opposed_embed_shows_winner():
    a = CheckResult(roll=10, skill=60, level=SuccessLevel.EXTREME)
    b = CheckResult(roll=50, skill=60, level=SuccessLevel.REGULAR)
    result = OpposedResult(a=a, b=b, winner="a")
    embed = opposed_embed(result, label_a="나", label_b="상대")
    winner_field = next(f for f in embed.fields if f.name == "결과")
    assert winner_field.value == "나 승리"


def test_opposed_embed_shows_tie():
    a = CheckResult(roll=20, skill=50, level=SuccessLevel.REGULAR)
    b = CheckResult(roll=20, skill=50, level=SuccessLevel.REGULAR)
    result = OpposedResult(a=a, b=b, winner="tie")
    embed = opposed_embed(result)
    winner_field = next(f for f in embed.fields if f.name == "결과")
    assert winner_field.value == "무승부"
