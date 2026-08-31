import pytest

from dice import DiceExpr, parse_dice_notation
from tests.test_dice_check import FakeRng


def test_parse_dice_notation_basic():
    expr = parse_dice_notation("1d4+1")
    assert expr == DiceExpr(count=1, sides=4, modifier=1)


def test_parse_dice_notation_no_modifier():
    expr = parse_dice_notation("2d6")
    assert expr == DiceExpr(count=2, sides=6, modifier=0)


def test_parse_dice_notation_negative_modifier():
    expr = parse_dice_notation("1d10-2")
    assert expr == DiceExpr(count=1, sides=10, modifier=-2)


def test_parse_dice_notation_strips_whitespace():
    expr = parse_dice_notation("  1d4 + 1  ")
    assert expr == DiceExpr(count=1, sides=4, modifier=1)


def test_parse_dice_notation_invalid_raises():
    with pytest.raises(ValueError):
        parse_dice_notation("not-a-dice")


def test_dice_expr_roll_sums_and_adds_modifier():
    rng = FakeRng([3, 2])
    expr = DiceExpr(count=2, sides=6, modifier=1)
    assert expr.roll(rng=rng) == 6  # 3 + 2 + 1
