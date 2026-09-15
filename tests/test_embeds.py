from bot.embeds import (
    character_embed,
    check_embed,
    keeper_narration_embed,
    narration_embed,
    opposed_embed,
    sanity_embed,
    scenario_embed,
)
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


def test_sanity_embed_shows_no_warnings_by_default():
    result = SanityResult(roll=20, current_san=50, success=True, loss=1, remaining_san=49)
    embed = sanity_embed(result)
    assert not any(f.name == "⚠️ 경고" for f in embed.fields)


def test_sanity_embed_shows_warnings():
    result = SanityResult(roll=80, current_san=50, success=False, loss=10, remaining_san=40)
    embed = sanity_embed(result, warnings=["일시적 광기 판정 필요"])
    warning_fields = [f.value for f in embed.fields if f.name == "⚠️ 경고"]
    assert warning_fields == ["일시적 광기 판정 필요"]


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


def _sample_character(**overrides):
    base = {
        "name": "탐사자",
        "occupation": "사립탐정",
        "str": 50, "dex": 60, "pow": 55, "con": 65, "app": 45,
        "edu": 70, "siz": 50, "int": 80, "mov": 8,
        "skills": {"회계": 5, "심리학": 10, "회피": 30},
    }
    base.update(overrides)
    return base


def test_character_embed_uses_character_name_as_title():
    embed = character_embed(_sample_character(), owner_name="플레이어닉네임")
    assert embed.title == "탐사자"


def test_character_embed_falls_back_to_owner_name_when_unnamed():
    embed = character_embed(_sample_character(name=None), owner_name="플레이어닉네임")
    assert embed.title == "플레이어닉네임"


def test_character_embed_shows_attributes():
    embed = character_embed(_sample_character(), owner_name="플레이어닉네임")
    attr_field = next(f for f in embed.fields if f.name == "특성치")
    assert "STR 50" in attr_field.value
    assert "INT 80" in attr_field.value


def test_character_embed_shows_top_skills():
    embed = character_embed(_sample_character(), owner_name="플레이어닉네임")
    skill_field = next(f for f in embed.fields if f.name == "주요 기능")
    assert "회피: 30" in skill_field.value


def test_narration_embed_shows_summary_and_purpose():
    embed = narration_embed("주변을 둘러본다", "상황을 파악하려 함")

    assert embed.description == "주변을 둘러본다"
    assert embed.fields[0].value == "상황을 파악하려 함"


def test_character_embed_shows_role_badge_for_npc():
    embed = character_embed(_sample_character(role="NPC", name="관리인"), owner_name="관리인")
    assert embed.title == "[NPC] 관리인"


def test_character_embed_omits_badge_for_pc():
    embed = character_embed(_sample_character(), owner_name="탐사자")
    assert embed.title == "탐사자"


def test_character_embed_shows_hp_mp_san():
    character = _sample_character(
        hp_current=11, hp_max=11, mp_current=11, mp_max=11, san_current=55, san_starting=55
    )
    embed = character_embed(character, owner_name="탐사자")
    vitals_field = next(f for f in embed.fields if f.name == "HP / MP / SAN")
    assert vitals_field.value == "HP 11/11  MP 11/11  SAN 55/55"


def test_character_embed_shows_retired_badge():
    embed = character_embed(_sample_character(is_retired=True), owner_name="탐사자")
    assert "퇴장" in embed.title


def test_scenario_embed_shows_title_progress_and_roster():
    scenario = {
        "title": "마지막 상영",
        "keeper_user_id": 999,
        "current_scene_index": 1,
        "structure": [{"scene": "장면 1"}, {"scene": "장면 2"}],
    }
    roster = [{"name": "탐사자A"}, {"name": "탐사자B"}]

    embed = scenario_embed(scenario, roster)

    assert embed.title == "마지막 상영"
    fields = {f.name: f.value for f in embed.fields}
    assert "999" in fields["키퍼"]
    assert fields["진행 위치"] == "장면 2 / 2"
    assert "탐사자A" in fields["참가자(PC)"]


def test_scenario_embed_shows_placeholder_for_empty_roster():
    scenario = {
        "title": "빈 시나리오", "keeper_user_id": 1,
        "current_scene_index": 0, "structure": [{"scene": "장면 1"}],
    }
    embed = scenario_embed(scenario, [])
    fields = {f.name: f.value for f in embed.fields}
    assert fields["참가자(PC)"] == "(없음)"


def test_keeper_narration_embed_shows_scene_and_line():
    embed = keeper_narration_embed("장면 1. 일상", "늦은 오후입니다.")
    assert embed.title == "장면 1. 일상"
    assert embed.description == "늦은 오후입니다."
