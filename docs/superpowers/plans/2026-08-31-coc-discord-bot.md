# CoC 판정 디스코드 봇 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Call of Cthulhu 7판 스킬 판정/SAN 체크/대립판정/푸시 롤을 자동화하는 상태 없는(stateless) 디스코드 슬래시 커맨드 봇을 구현한다.

**Architecture:** 판정 로직(`dice.py`)은 discord 비의존 순수 함수로 구현해 pytest로 검증한다. discord.py 슬래시 커맨드(`bot/cogs/*.py`)는 이 순수 함수를 호출해 결과를 임베드(`bot/embeds.py`)로 포맷해 응답하는 얇은 어댑터 계층이다. 캐릭터/시나리오 데이터를 저장하지 않으므로 DB가 없다. 유일한 상태는 푸시 롤용 `discord.ui.View` 인스턴스가 메모리에 들고 있는 직전 판정 정보뿐이다.

**Tech Stack:** Python 3.12+, discord.py, pytest

**Spec:** `docs/superpowers/specs/2026-08-31-coc-discord-bot-design.md`

## Global Constraints

- Python 3.12 이상, discord.py 2.4 이상 (`requirements.txt`에 고정)
- 사용자에게 보이는 모든 텍스트(임베드, 에러 메시지, 커맨드/옵션 설명)는 한국어
- DB나 파일 기반 영속 저장소를 두지 않는다 — stateless 설계 유지
- `discord.py`, `pytest` 외 새 의존성을 추가하지 않는다
- 모든 판정 계산 로직은 `dice.py`에 discord 비의존 순수 함수로 구현한다 (테스트 용이성)
- `DISCORD_TOKEN`을 코드나 커밋에 하드코딩하지 않는다 — 환경변수로만 주입

---

## Task 1: 핵심 d100 판정 + 성공등급 (보너스/페널티 포함)

**Files:**
- Create: `dice.py`
- Create: `requirements.txt`
- Create: `pytest.ini`
- Test: `tests/test_dice_check.py`

**Interfaces:**
- Produces: `SuccessLevel` (Enum: CRITICAL, EXTREME, HARD, REGULAR, FAIL, FUMBLE), `SUCCESS_LEVELS_RANKED: list[SuccessLevel]` (fumble→critical 오름차순), `is_success(level: SuccessLevel) -> bool`, `determine_success_level(roll: int, skill: int) -> SuccessLevel`, `CheckResult` (dataclass: `roll: int, skill: int, level: SuccessLevel`), `roll_d100(bonus: int = 0, penalty: int = 0, rng=random) -> int`, `roll_check(skill: int, bonus: int = 0, penalty: int = 0, rng=random) -> CheckResult`

- [ ] **Step 1: 테스트 디렉터리와 픽스처 준비**

`tests/test_dice_check.py` 파일을 만들고 결정론적 난수를 위한 `FakeRng`를 정의한다.

```python
class FakeRng:
    """randint 호출마다 미리 정해둔 값을 순서대로 반환하는 테스트용 rng."""

    def __init__(self, values):
        self.values = list(values)

    def randint(self, a, b):
        return self.values.pop(0)
```

- [ ] **Step 2: 실패하는 테스트 작성**

같은 파일에 이어서 작성:

```python
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
    assert result == CheckResult(roll=30, skill=60, level=SuccessLevel.REGULAR)
```

- [ ] **Step 3: 테스트 실행해 실패 확인**

Run: `pytest tests/test_dice_check.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'dice'` 등, 아직 구현 없음)

- [ ] **Step 4: `dice.py` 구현**

```python
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
```

- [ ] **Step 5: `requirements.txt`, `pytest.ini` 작성**

`requirements.txt`:

```
discord.py>=2.4
pytest>=8.0
```

`pytest.ini`:

```ini
[pytest]
pythonpath = .
```

- [ ] **Step 6: 가상환경 준비 후 테스트 실행해 통과 확인**

Run:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest tests/test_dice_check.py -v
```
Expected: 모든 테스트 PASS

- [ ] **Step 7: 커밋**

```bash
git add dice.py requirements.txt pytest.ini tests/test_dice_check.py
git commit -m "feat: add core d100 check with bonus/penalty dice and success levels"
```

---

## Task 2: 다이스 표기 파서 (`XdY+Z`)

**Files:**
- Modify: `dice.py`
- Test: `tests/test_dice_notation.py`

**Interfaces:**
- Consumes: (독립적, Task 1과 무관)
- Produces: `DiceExpr` (dataclass: `count: int, sides: int, modifier: int = 0`, 메서드 `roll(rng=random) -> int`), `parse_dice_notation(text: str) -> DiceExpr` (형식 오류 시 `ValueError`)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_dice_notation.py`:

```python
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
```

`tests/test_dice_check.py`에서 `FakeRng`를 다른 테스트 파일이 재사용할 수 있도록 이미 모듈 최상단에 정의되어 있으므로 추가 작업은 없다. `tests/` 디렉터리에 `__init__.py`가 없다면 빈 파일로 만들어 패키지로 임포트 가능하게 한다.

- [ ] **Step 2: `tests/__init__.py` 생성**

빈 파일로 생성한다 (`tests` 디렉터리를 패키지로 만들어 `from tests.test_dice_check import FakeRng`가 동작하게 함).

- [ ] **Step 3: 테스트 실행해 실패 확인**

Run: `pytest tests/test_dice_notation.py -v`
Expected: FAIL (`ImportError: cannot import name 'DiceExpr'`)

- [ ] **Step 4: `dice.py`에 파서 추가**

`dice.py` 상단에 `import re` 추가, 파일 끝에 이어서 작성:

```python
_DICE_RE = re.compile(r"^(\d+)d(\d+)([+-]\d+)?$")


@dataclass
class DiceExpr:
    count: int
    sides: int
    modifier: int = 0

    def roll(self, rng: random.Random = random) -> int:
        return sum(rng.randint(1, self.sides) for _ in range(self.count)) + self.modifier


def parse_dice_notation(text: str) -> DiceExpr:
    normalized = text.strip().replace(" ", "")
    match = _DICE_RE.match(normalized)
    if not match:
        raise ValueError(f"올바르지 않은 주사위 표기입니다: {text}")
    count, sides, modifier = match.groups()
    return DiceExpr(
        count=int(count), sides=int(sides), modifier=int(modifier) if modifier else 0
    )
```

- [ ] **Step 5: 테스트 실행해 통과 확인**

Run: `pytest tests/test_dice_notation.py -v`
Expected: 모든 테스트 PASS

- [ ] **Step 6: 커밋**

```bash
git add dice.py tests/__init__.py tests/test_dice_notation.py
git commit -m "feat: add dice notation parser (XdY+Z)"
```

---

## Task 3: SAN 체크

**Files:**
- Modify: `dice.py`
- Test: `tests/test_sanity.py`

**Interfaces:**
- Consumes: `DiceExpr`, `parse_dice_notation` (Task 2), `roll_d100` (Task 1)
- Produces: `SanityResult` (dataclass: `roll: int, current_san: int, success: bool, loss: int, remaining_san: int`), `parse_san_formula(text: str) -> tuple[DiceExpr, DiceExpr]` (형식: `"성공손실/실패손실"`, 각 항은 정수 또는 다이스 표기), `sanity_check(current_san: int, formula: str, rng=random) -> SanityResult`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_sanity.py`:

```python
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
```

- [ ] **Step 2: 테스트 실행해 실패 확인**

Run: `pytest tests/test_sanity.py -v`
Expected: FAIL (`ImportError: cannot import name 'parse_san_formula'`)

- [ ] **Step 3: `dice.py`에 SAN 체크 추가**

파일 끝에 이어서 작성:

```python
def _parse_san_side(text: str) -> DiceExpr:
    text = text.strip()
    if text.lstrip("-").isdigit():
        return DiceExpr(count=0, sides=0, modifier=int(text))
    return parse_dice_notation(text)


def parse_san_formula(text: str) -> tuple[DiceExpr, DiceExpr]:
    parts = text.strip().split("/")
    if len(parts) != 2:
        raise ValueError(
            f"SAN 손실식은 '성공손실/실패손실' 형식이어야 합니다 (예: 1/1d4+1): {text}"
        )
    return _parse_san_side(parts[0]), _parse_san_side(parts[1])


@dataclass
class SanityResult:
    roll: int
    current_san: int
    success: bool
    loss: int
    remaining_san: int


def sanity_check(
    current_san: int, formula: str, rng: random.Random = random
) -> SanityResult:
    success_loss, fail_loss = parse_san_formula(formula)
    roll = roll_d100(rng=rng)
    success = roll <= current_san
    loss_expr = success_loss if success else fail_loss
    loss = loss_expr.roll(rng=rng)
    remaining = max(0, current_san - loss)
    return SanityResult(
        roll=roll, current_san=current_san, success=success, loss=loss, remaining_san=remaining
    )
```

- [ ] **Step 4: 테스트 실행해 통과 확인**

Run: `pytest tests/test_sanity.py -v`
Expected: 모든 테스트 PASS

- [ ] **Step 5: 커밋**

```bash
git add dice.py tests/test_sanity.py
git commit -m "feat: add SAN formula parsing and sanity_check"
```

---

## Task 4: 대립판정 (Opposed Roll)

**Files:**
- Modify: `dice.py`
- Test: `tests/test_opposed.py`

**Interfaces:**
- Consumes: `roll_check`, `CheckResult`, `SuccessLevel`, `SUCCESS_LEVELS_RANKED` (Task 1)
- Produces: `OpposedResult` (dataclass: `a: CheckResult, b: CheckResult, winner: str` — `"a"`, `"b"`, `"tie"` 중 하나), `opposed_check(skill_a: int, skill_b: int, rng=random) -> OpposedResult`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_opposed.py`:

```python
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
```

- [ ] **Step 2: 테스트 실행해 실패 확인**

Run: `pytest tests/test_opposed.py -v`
Expected: FAIL (`ImportError: cannot import name 'opposed_check'`)

- [ ] **Step 3: `dice.py`에 대립판정 추가**

파일 끝에 이어서 작성:

```python
_LEVEL_RANK = {level: i for i, level in enumerate(SUCCESS_LEVELS_RANKED)}


@dataclass
class OpposedResult:
    a: CheckResult
    b: CheckResult
    winner: str


def opposed_check(skill_a: int, skill_b: int, rng: random.Random = random) -> OpposedResult:
    result_a = roll_check(skill_a, rng=rng)
    result_b = roll_check(skill_b, rng=rng)
    rank_a = _LEVEL_RANK[result_a.level]
    rank_b = _LEVEL_RANK[result_b.level]
    if rank_a > rank_b:
        winner = "a"
    elif rank_b > rank_a:
        winner = "b"
    elif skill_a == skill_b:
        winner = "tie"
    else:
        winner = "a" if skill_a > skill_b else "b"
    return OpposedResult(a=result_a, b=result_b, winner=winner)
```

- [ ] **Step 4: 테스트 실행해 통과 확인**

Run: `pytest tests/test_opposed.py -v`
Expected: 모든 테스트 PASS

- [ ] **Step 5: 커밋**

```bash
git add dice.py tests/test_opposed.py
git commit -m "feat: add opposed_check"
```

---

## Task 5: 임베드 포맷 (`bot/embeds.py`)

**Files:**
- Create: `bot/__init__.py`
- Create: `bot/embeds.py`
- Test: `tests/test_embeds.py`

**Interfaces:**
- Consumes: `CheckResult`, `SanityResult`, `OpposedResult`, `SuccessLevel` (`dice.py`, Tasks 1/3/4)
- Produces: `check_embed(result: CheckResult, label: str = "판정") -> discord.Embed`, `sanity_embed(result: SanityResult) -> discord.Embed`, `opposed_embed(result: OpposedResult, label_a: str = "A", label_b: str = "B") -> discord.Embed`

- [ ] **Step 1: `bot/__init__.py` 빈 파일 생성**

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/test_embeds.py`:

```python
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
```

- [ ] **Step 3: 테스트 실행해 실패 확인**

Run: `pytest tests/test_embeds.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'bot'`)

- [ ] **Step 4: `bot/embeds.py` 구현**

```python
import discord

from dice import CheckResult, OpposedResult, SanityResult, SuccessLevel

_LEVEL_LABELS = {
    SuccessLevel.CRITICAL: "크리티컬 성공",
    SuccessLevel.EXTREME: "익스트림 성공",
    SuccessLevel.HARD: "하드 성공",
    SuccessLevel.REGULAR: "성공",
    SuccessLevel.FAIL: "실패",
    SuccessLevel.FUMBLE: "펌블",
}

_SUCCESS_COLOR = discord.Color.green()
_FAIL_COLOR = discord.Color.red()


def _level_color(level: SuccessLevel) -> discord.Color:
    return _FAIL_COLOR if level in (SuccessLevel.FAIL, SuccessLevel.FUMBLE) else _SUCCESS_COLOR


def check_embed(result: CheckResult, label: str = "판정") -> discord.Embed:
    embed = discord.Embed(
        title=label,
        description=f"1D100 = **{result.roll}** / 스킬값 {result.skill}",
        color=_level_color(result.level),
    )
    embed.add_field(name="결과", value=_LEVEL_LABELS[result.level])
    return embed


def sanity_embed(result: SanityResult) -> discord.Embed:
    outcome = "성공" if result.success else "실패"
    embed = discord.Embed(
        title="SAN 체크",
        description=f"1D100 = **{result.roll}** / 현재 SAN {result.current_san}",
        color=_SUCCESS_COLOR if result.success else _FAIL_COLOR,
    )
    embed.add_field(name="결과", value=outcome)
    embed.add_field(name="SAN 손실", value=f"-{result.loss}")
    embed.add_field(name="남은 SAN", value=str(result.remaining_san))
    return embed


def opposed_embed(
    result: OpposedResult, label_a: str = "A", label_b: str = "B"
) -> discord.Embed:
    winner_text = {
        "a": f"{label_a} 승리",
        "b": f"{label_b} 승리",
        "tie": "무승부",
    }[result.winner]
    embed = discord.Embed(title="대립판정", color=discord.Color.blurple())
    embed.add_field(
        name=label_a, value=f"{result.a.roll} → {_LEVEL_LABELS[result.a.level]}", inline=True
    )
    embed.add_field(
        name=label_b, value=f"{result.b.roll} → {_LEVEL_LABELS[result.b.level]}", inline=True
    )
    embed.add_field(name="결과", value=winner_text, inline=False)
    return embed
```

- [ ] **Step 5: 테스트 실행해 통과 확인**

Run: `pytest tests/test_embeds.py -v`
Expected: 모든 테스트 PASS

- [ ] **Step 6: 커밋**

```bash
git add bot/__init__.py bot/embeds.py tests/test_embeds.py
git commit -m "feat: add Korean embed formatting for check/sanity/opposed results"
```

---

## Task 6: 봇 스켈레톤 (`bot/main.py`)

**Files:**
- Create: `bot/main.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: (discord.py 라이브러리만)
- Produces: `CoCBot` (commands.Bot 서브클래스, `setup_hook`에서 `bot.cogs.check`/`bot.cogs.sanity`/`bot.cogs.opposed` extension 로드 후 `tree.sync()`), 모듈 수준 `bot: CoCBot` 인스턴스, `on_app_command_error(interaction, error)` 에러 핸들러, `main() -> None` (환경변수 `DISCORD_TOKEN` 없으면 `SystemExit`)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_main.py`:

```python
import pytest

import bot.main as main_module


def test_main_raises_systemexit_without_token(monkeypatch):
    monkeypatch.delenv("DISCORD_TOKEN", raising=False)
    with pytest.raises(SystemExit):
        main_module.main()
```

- [ ] **Step 2: 테스트 실행해 실패 확인**

Run: `pytest tests/test_main.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'bot.main'`)

- [ ] **Step 3: `bot/main.py` 구현**

```python
import logging
import os

import discord
from discord import app_commands
from discord.ext import commands

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("coc-bot")

INTENTS = discord.Intents.default()


class CoCBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix="!coc-unused!", intents=INTENTS)

    async def setup_hook(self) -> None:
        await self.load_extension("bot.cogs.check")
        await self.load_extension("bot.cogs.sanity")
        await self.load_extension("bot.cogs.opposed")
        await self.tree.sync()


bot = CoCBot()


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
) -> None:
    logger.exception("Slash command error", exc_info=error)
    original = getattr(error, "original", error)
    message = str(original) if isinstance(original, ValueError) else "명령어 처리 중 오류가 발생했습니다."
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


def main() -> None:
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise SystemExit("DISCORD_TOKEN 환경변수가 설정되지 않았습니다.")
    bot.run(token)


if __name__ == "__main__":
    main()
```

이 시점에는 `bot/cogs/` 패키지가 아직 없어 `bot.run()`을 실제로 호출하는 경로는 동작하지 않지만, Task 7~9에서 cog가 추가되기 전까지는 `main()`의 토큰 가드 절만 테스트 대상이므로 문제가 되지 않는다.

- [ ] **Step 4: 테스트 실행해 통과 확인**

Run: `pytest tests/test_main.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add bot/main.py tests/test_main.py
git commit -m "feat: add bot skeleton with cog loader and error handler"
```

---

## Task 7: `/판정` 커맨드 + 푸시 롤 버튼

**Files:**
- Create: `bot/cogs/__init__.py`
- Create: `bot/cogs/check.py`
- Test: `tests/test_check_cog.py`

**Interfaces:**
- Consumes: `roll_check`, `is_success` (`dice.py`, Task 1), `check_embed` (`bot/embeds.py`, Task 5)
- Produces: `PushView` (discord.ui.View, `__init__(self, skill, bonus, penalty)`), `CheckCog` (commands.Cog, 슬래시 커맨드 `check` 메서드에 `app_commands.command(name="판정")` 적용, 파라미터 `스킬값/보너스/페널티`), 모듈 수준 `async def setup(bot) -> None`

- [ ] **Step 1: `bot/cogs/__init__.py` 빈 파일 생성**

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/test_check_cog.py`:

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.check import CheckCog, PushView
from dice import CheckResult, SuccessLevel


def _make_interaction():
    interaction = MagicMock()
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    return interaction


def test_check_attaches_push_view_on_failure(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.check.roll_check",
        lambda skill, bonus=0, penalty=0: CheckResult(roll=90, skill=skill, level=SuccessLevel.FAIL),
    )
    cog = CheckCog(bot=MagicMock())
    interaction = _make_interaction()

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

    _, kwargs = interaction.response.send_message.call_args
    assert kwargs["view"] is None


def test_push_view_reroll_disables_button_and_sends_followup(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.check.roll_check",
        lambda skill, bonus=0, penalty=0: CheckResult(roll=5, skill=skill, level=SuccessLevel.EXTREME),
    )
    view = PushView(skill=50, bonus=0, penalty=0)
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
    view = PushView(skill=50, bonus=0, penalty=0)
    view.pushed = True
    interaction = _make_interaction()

    asyncio.run(view.push.callback(interaction))

    interaction.response.send_message.assert_awaited_once_with("이미 푸시했습니다.", ephemeral=True)
    interaction.response.edit_message.assert_not_called()
```

- [ ] **Step 3: 테스트 실행해 실패 확인**

Run: `pytest tests/test_check_cog.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'bot.cogs.check'`)

- [ ] **Step 4: `bot/cogs/check.py` 구현**

```python
import discord
from discord import app_commands
from discord.ext import commands

from bot.embeds import check_embed
from dice import is_success, roll_check


class PushView(discord.ui.View):
    def __init__(self, skill: int, bonus: int, penalty: int) -> None:
        super().__init__(timeout=300)
        self.skill = skill
        self.bonus = bonus
        self.penalty = penalty
        self.pushed = False

    @discord.ui.button(label="푸시", style=discord.ButtonStyle.danger)
    async def push(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.pushed:
            await interaction.response.send_message("이미 푸시했습니다.", ephemeral=True)
            return
        self.pushed = True
        button.disabled = True
        result = roll_check(self.skill, bonus=self.bonus, penalty=self.penalty)
        embed = check_embed(result, label="푸시 판정")
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(embed=embed)


class CheckCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="판정", description="CoC 스킬 판정을 굴립니다.")
    @app_commands.describe(
        스킬값="판정할 스킬 값 (0-100)",
        보너스="보너스 주사위 개수 (0-2)",
        페널티="페널티 주사위 개수 (0-2)",
    )
    async def check(
        self,
        interaction: discord.Interaction,
        스킬값: app_commands.Range[int, 0, 100],
        보너스: app_commands.Range[int, 0, 2] = 0,
        페널티: app_commands.Range[int, 0, 2] = 0,
    ) -> None:
        result = roll_check(스킬값, bonus=보너스, penalty=페널티)
        embed = check_embed(result)
        view = None if is_success(result.level) else PushView(스킬값, 보너스, 페널티)
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CheckCog(bot))
```

- [ ] **Step 5: 테스트 실행해 통과 확인**

Run: `pytest tests/test_check_cog.py -v`
Expected: 모든 테스트 PASS

- [ ] **Step 6: 봇 전체 테스트 스위트 실행**

Run: `pytest -v`
Expected: 모든 테스트 PASS (Task 6의 `test_main.py`가 이제 `bot.cogs.check`를 정상적으로 찾을 수 있음)

- [ ] **Step 7: 커밋**

```bash
git add bot/cogs/__init__.py bot/cogs/check.py tests/test_check_cog.py
git commit -m "feat: add /판정 slash command with push-roll button"
```

---

## Task 8: `/산정` 커맨드

**Files:**
- Create: `bot/cogs/sanity.py`
- Test: `tests/test_sanity_cog.py`

**Interfaces:**
- Consumes: `sanity_check` (`dice.py`, Task 3), `sanity_embed` (`bot/embeds.py`, Task 5)
- Produces: `SanityCog` (commands.Cog, 슬래시 커맨드 `sanity` 메서드에 `app_commands.command(name="산정")` 적용, 파라미터 `현재san/손실식`), 모듈 수준 `async def setup(bot) -> None`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_sanity_cog.py`:

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.sanity import SanityCog
from dice import SanityResult


def _make_interaction():
    interaction = MagicMock()
    interaction.response = AsyncMock()
    return interaction


def test_sanity_command_sends_embed(monkeypatch):
    monkeypatch.setattr(
        "bot.cogs.sanity.sanity_check",
        lambda current_san, formula: SanityResult(
            roll=20, current_san=current_san, success=True, loss=1, remaining_san=current_san - 1
        ),
    )
    cog = SanityCog(bot=MagicMock())
    interaction = _make_interaction()

    asyncio.run(cog.sanity.callback(cog, interaction, 현재san=50, 손실식="1/1d4+1"))

    interaction.response.send_message.assert_awaited_once()
    _, kwargs = interaction.response.send_message.call_args
    assert kwargs["embed"] is not None
```

- [ ] **Step 2: 테스트 실행해 실패 확인**

Run: `pytest tests/test_sanity_cog.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'bot.cogs.sanity'`)

- [ ] **Step 3: `bot/cogs/sanity.py` 구현**

```python
import discord
from discord import app_commands
from discord.ext import commands

from bot.embeds import sanity_embed
from dice import sanity_check


class SanityCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="산정", description="SAN 체크를 굴립니다.")
    @app_commands.describe(
        현재san="현재 SAN 값",
        손실식="성공손실/실패손실 형식 (예: 1/1d4+1)",
    )
    async def sanity(
        self,
        interaction: discord.Interaction,
        현재san: app_commands.Range[int, 0, 99],
        손실식: str,
    ) -> None:
        result = sanity_check(현재san, 손실식)
        await interaction.response.send_message(embed=sanity_embed(result))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SanityCog(bot))
```

`sanity_check`가 잘못된 `손실식`에 대해 `ValueError`를 던지면 Task 6의 전역 에러 핸들러(`on_app_command_error`)가 그 메시지를 그대로 ephemeral 응답으로 보여준다 — 이 cog에서 별도로 잡지 않는다.

- [ ] **Step 4: 테스트 실행해 통과 확인**

Run: `pytest tests/test_sanity_cog.py -v`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add bot/cogs/sanity.py tests/test_sanity_cog.py
git commit -m "feat: add /산정 slash command"
```

---

## Task 9: `/대립` 커맨드

**Files:**
- Create: `bot/cogs/opposed.py`
- Test: `tests/test_opposed_cog.py`

**Interfaces:**
- Consumes: `opposed_check` (`dice.py`, Task 4), `opposed_embed` (`bot/embeds.py`, Task 5)
- Produces: `OpposedCog` (commands.Cog, 슬래시 커맨드 `opposed` 메서드에 `app_commands.command(name="대립")` 적용, 파라미터 `내스킬/상대스킬`), 모듈 수준 `async def setup(bot) -> None`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_opposed_cog.py`:

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock

from bot.cogs.opposed import OpposedCog
from dice import CheckResult, OpposedResult, SuccessLevel


def _make_interaction():
    interaction = MagicMock()
    interaction.response = AsyncMock()
    return interaction


def test_opposed_command_sends_embed(monkeypatch):
    a = CheckResult(roll=10, skill=60, level=SuccessLevel.EXTREME)
    b = CheckResult(roll=50, skill=40, level=SuccessLevel.REGULAR)
    monkeypatch.setattr(
        "bot.cogs.opposed.opposed_check",
        lambda skill_a, skill_b: OpposedResult(a=a, b=b, winner="a"),
    )
    cog = OpposedCog(bot=MagicMock())
    interaction = _make_interaction()

    asyncio.run(cog.opposed.callback(cog, interaction, 내스킬=60, 상대스킬=40))

    interaction.response.send_message.assert_awaited_once()
    _, kwargs = interaction.response.send_message.call_args
    assert kwargs["embed"] is not None
```

- [ ] **Step 2: 테스트 실행해 실패 확인**

Run: `pytest tests/test_opposed_cog.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'bot.cogs.opposed'`)

- [ ] **Step 3: `bot/cogs/opposed.py` 구현**

```python
import discord
from discord import app_commands
from discord.ext import commands

from bot.embeds import opposed_embed
from dice import opposed_check


class OpposedCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="대립", description="두 스킬을 대립판정합니다.")
    @app_commands.describe(내스킬="내 스킬 값 (0-100)", 상대스킬="상대 스킬 값 (0-100)")
    async def opposed(
        self,
        interaction: discord.Interaction,
        내스킬: app_commands.Range[int, 0, 100],
        상대스킬: app_commands.Range[int, 0, 100],
    ) -> None:
        result = opposed_check(내스킬, 상대스킬)
        embed = opposed_embed(result, label_a="나", label_b="상대")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(OpposedCog(bot))
```

- [ ] **Step 4: 테스트 실행해 통과 확인**

Run: `pytest tests/test_opposed_cog.py -v`
Expected: PASS

- [ ] **Step 5: 전체 테스트 스위트 실행**

Run: `pytest -v`
Expected: 모든 테스트 PASS — 이제 `bot/cogs/`에 세 cog(`check`, `sanity`, `opposed`)가 모두 존재하므로 `bot.main`이 `setup_hook`에서 로드할 대상이 전부 갖춰졌다.

- [ ] **Step 6: 커밋**

```bash
git add bot/cogs/opposed.py tests/test_opposed_cog.py
git commit -m "feat: add /대립 slash command"
```

---

## Task 10: 배포 준비 (Dockerfile, README, .env.example)

**Files:**
- Create: `Dockerfile`
- Create: `.env.example`
- Create: `README.md`

**Interfaces:**
- Consumes: (없음 — 문서/배포 설정)
- Produces: (없음 — 코드 인터페이스 아님)

- [ ] **Step 1: `.env.example` 작성**

```
DISCORD_TOKEN=
```

- [ ] **Step 2: `Dockerfile` 작성**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "bot.main"]
```

- [ ] **Step 3: `README.md` 작성**

```markdown
# CoC-Bot

Call of Cthulhu 7판 판정(스킬 체크, SAN 체크, 대립판정, 푸시 롤)을 자동화하는
디스코드 슬래시 커맨드 봇. 캐릭터시트나 시나리오는 저장하지 않는다 — 사람 키퍼가
직접 진행하고, 봇은 판정 계산만 담당한다.

## 커맨드

- `/판정 스킬값 [보너스] [페널티]` — d100 판정, 실패 시 푸시 버튼 첨부
- `/산정 현재san 손실식` — SAN 체크 (손실식 예: `1/1d4+1`)
- `/대립 내스킬 상대스킬` — 대립판정

## 로컬 실행

1. [Discord Developer Portal](https://discord.com/developers/applications)에서
   애플리케이션/봇을 만들고 토큰을 발급받는다.
2. `applications.commands`, `bot` 스코프로 서버에 초대한다.
3. 의존성 설치 및 실행:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DISCORD_TOKEN=발급받은_토큰
python -m bot.main
```

## Docker로 실행

```bash
docker build -t coc-bot .
docker run -e DISCORD_TOKEN=발급받은_토큰 coc-bot
```

## 저비용 호스팅

DB 없이 프로세스 하나만 24/7 떠 있으면 되므로, 1 vCPU / 512MB급의 저사양
인스턴스로 충분하다. 무료/저가 티어를 제공하는 컨테이너 호스팅(Fly.io, Railway
등)이나 소형 VPS 어디에 올려도 된다.

## 테스트

```bash
pytest -v
```
```

- [ ] **Step 4: Docker 빌드로 수동 검증**

Run: `docker build -t coc-bot .`
Expected: 빌드 성공 (이미지가 정상적으로 생성됨)

- [ ] **Step 5: 커밋**

```bash
git add Dockerfile .env.example README.md
git commit -m "docs: add Dockerfile, README, and env example for deployment"
```
