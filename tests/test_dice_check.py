class FakeRng:
    """randint 호출마다 미리 정해둔 값을 순서대로 반환하는 테스트용 rng."""

    def __init__(self, values):
        self.values = list(values)

    def randint(self, a, b):
        return self.values.pop(0)


from dice import (
    CheckResult,
    SuccessLevel,
    determine_success_level,
    is_success,
    roll_check,
    roll_d100,
)


def test_roll_of_1_is_always_critical():
    assert determine_success_level(1, skill=10) == SuccessLevel.CRITICAL


def test_fumble_threshold_low_skill():
    # skill < 50 이면 96-100이 펌블
    assert determine_success_level(96, skill=40) == SuccessLevel.FUMBLE
    assert determine_success_level(95, skill=40) == SuccessLevel.FAIL


def test_fumble_threshold_high_skill():
    # skill >= 50 이면 100만 펌블
    assert determine_success_level(100, skill=60) == SuccessLevel.FUMBLE
    assert determine_success_level(97, skill=60) == SuccessLevel.FAIL


def test_extreme_hard_regular_boundaries():
    skill = 60  # extreme<=12, hard<=30, regular<=60
    assert determine_success_level(12, skill) == SuccessLevel.EXTREME
    assert determine_success_level(13, skill) == SuccessLevel.HARD
    assert determine_success_level(30, skill) == SuccessLevel.HARD
    assert determine_success_level(31, skill) == SuccessLevel.REGULAR
    assert determine_success_level(60, skill) == SuccessLevel.REGULAR
    assert determine_success_level(61, skill) == SuccessLevel.FAIL


def test_is_success():
    assert is_success(SuccessLevel.REGULAR) is True
    assert is_success(SuccessLevel.EXTREME) is True
    assert is_success(SuccessLevel.FAIL) is False
    assert is_success(SuccessLevel.FUMBLE) is False


def test_roll_d100_no_bonus_penalty():
    # ones=3, tens=7 -> roll 73
    rng = FakeRng([3, 7])
    assert roll_d100(rng=rng) == 73


def test_roll_d100_zero_becomes_100():
    rng = FakeRng([0, 0])
    assert roll_d100(rng=rng) == 100


def test_roll_d100_bonus_picks_lower_tens():
    # ones=5, tens 후보 [8, 2] -> 보너스는 낮은 값(2) 채택 -> 25
    rng = FakeRng([5, 8, 2])
    assert roll_d100(bonus=1, rng=rng) == 25


def test_roll_d100_penalty_picks_higher_tens():
    # ones=5, tens 후보 [8, 2] -> 페널티는 높은 값(8) 채택 -> 85
    rng = FakeRng([5, 8, 2])
    assert roll_d100(penalty=1, rng=rng) == 85


def test_roll_d100_bonus_and_penalty_cancel_out():
    # bonus=1, penalty=1 -> net 0 -> 추가 주사위 없이 단일 tens만 사용
    rng = FakeRng([5, 8])
    assert roll_d100(bonus=1, penalty=1, rng=rng) == 85


def test_roll_d100_caps_at_two_extra_dice():
    # bonus=5는 2로 clamp -> tens 후보 3개 중 최솟값 채택
    rng = FakeRng([5, 9, 4, 1])
    assert roll_d100(bonus=5, rng=rng) == 15


def test_roll_check_returns_result_with_level():
    rng = FakeRng([0, 3])  # roll = 30
    result = roll_check(skill=60, rng=rng)
    assert result == CheckResult(roll=30, skill=60, level=SuccessLevel.HARD)
