import pytest

from dice import DiceExpr, SanityResult, parse_san_formula, sanity_check
from tests.test_dice_check import FakeRng


def test_parse_san_formula_dice_both_sides():
    success, fail = parse_san_formula("1/1d4+1")
    assert success == DiceExpr(count=0, sides=0, modifier=1)
    assert fail == DiceExpr(count=1, sides=4, modifier=1)


def test_parse_san_formula_dice_both_random():
    success, fail = parse_san_formula("1d2/1d6")
    assert success == DiceExpr(count=1, sides=2, modifier=0)
    assert fail == DiceExpr(count=1, sides=6, modifier=0)


def test_parse_san_formula_invalid_raises():
    with pytest.raises(ValueError):
        parse_san_formula("1d4+1")  # 슬래시 없음


def test_sanity_check_success():
    # roll 1D100 -> ones=0,tens=2 => 20 <= current_san(50) => 성공, 성공손실(1) 적용
    rng = FakeRng([0, 2])
    result = sanity_check(current_san=50, formula="1/1d4+1", rng=rng)
    assert result == SanityResult(
        roll=20, current_san=50, success=True, loss=1, remaining_san=49
    )


def test_sanity_check_failure_rolls_fail_dice():
    # roll 1D100 -> 80 > current_san(50) => 실패. 이어서 실패손실 1d4+1 굴림: 3+1=4
    rng = FakeRng([0, 8, 3])
    result = sanity_check(current_san=50, formula="1/1d4+1", rng=rng)
    assert result == SanityResult(
        roll=80, current_san=50, success=False, loss=4, remaining_san=46
    )


def test_sanity_check_remaining_san_floored_at_zero():
    rng = FakeRng([0, 8, 9])  # roll=80 실패, loss=9+1=10
    result = sanity_check(current_san=5, formula="1/1d8+1", rng=rng)
    assert result.remaining_san == 0
