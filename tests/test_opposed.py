from dice import CheckResult, OpposedResult, SuccessLevel, opposed_check
from tests.test_dice_check import FakeRng


def test_opposed_higher_success_level_wins():
    # a: roll=10,skill=60 -> HARD(<=30... 실제로 10<=12=extreme). 명확히 하기 위해 별도 계산.
    # a ones=0,tens=1 -> roll=10, skill=60 -> extreme(<=12)
    # b ones=0,tens=5 -> roll=50, skill=60 -> regular
    rng = FakeRng([0, 1, 0, 5])
    result = opposed_check(skill_a=60, skill_b=60, rng=rng)
    assert result.a == CheckResult(roll=10, skill=60, level=SuccessLevel.EXTREME)
    assert result.b == CheckResult(roll=50, skill=60, level=SuccessLevel.REGULAR)
    assert result.winner == "a"


def test_opposed_tie_break_by_higher_skill():
    # 둘 다 regular: a roll=20/skill=40, b roll=20/skill=80 -> 같은 등급이면 스킬 높은 쪽 승리
    rng = FakeRng([0, 2, 0, 2])
    result = opposed_check(skill_a=40, skill_b=80, rng=rng)
    assert result.winner == "b"


def test_opposed_true_tie_same_skill_same_level():
    rng = FakeRng([0, 2, 0, 2])  # 둘 다 roll=20
    result = opposed_check(skill_a=50, skill_b=50, rng=rng)
    assert result.winner == "tie"
