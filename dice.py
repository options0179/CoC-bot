import random
from dataclasses import dataclass
from enum import Enum


class SuccessLevel(Enum):
    CRITICAL = "critical"
    EXTREME = "extreme"
    HARD = "hard"
    REGULAR = "regular"
    FAIL = "fail"
    FUMBLE = "fumble"


SUCCESS_LEVELS_RANKED = [
    SuccessLevel.FUMBLE,
    SuccessLevel.FAIL,
    SuccessLevel.REGULAR,
    SuccessLevel.HARD,
    SuccessLevel.EXTREME,
    SuccessLevel.CRITICAL,
]


def is_success(level: SuccessLevel) -> bool:
    return level not in (SuccessLevel.FAIL, SuccessLevel.FUMBLE)


def determine_success_level(roll: int, skill: int) -> SuccessLevel:
    if roll == 1:
        return SuccessLevel.CRITICAL
    fumble_threshold = 96 if skill < 50 else 100
    if roll >= fumble_threshold:
        return SuccessLevel.FUMBLE
    if roll <= skill // 5:
        return SuccessLevel.EXTREME
    if roll <= skill // 2:
        return SuccessLevel.HARD
    if roll <= skill:
        return SuccessLevel.REGULAR
    return SuccessLevel.FAIL


@dataclass
class CheckResult:
    roll: int
    skill: int
    level: SuccessLevel


def roll_d100(bonus: int = 0, penalty: int = 0, rng: random.Random = random) -> int:
    net = max(-2, min(2, bonus - penalty))
    ones = rng.randint(0, 9)
    tens_options = [rng.randint(0, 9) for _ in range(1 + abs(net))]
    if net > 0:
        tens = min(tens_options)
    elif net < 0:
        tens = max(tens_options)
    else:
        tens = tens_options[0]
    roll = tens * 10 + ones
    return 100 if roll == 0 else roll


def roll_check(
    skill: int, bonus: int = 0, penalty: int = 0, rng: random.Random = random
) -> CheckResult:
    roll = roll_d100(bonus=bonus, penalty=penalty, rng=rng)
    return CheckResult(roll=roll, skill=skill, level=determine_success_level(roll, skill))
