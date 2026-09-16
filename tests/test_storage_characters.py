import asyncio
import os

import pytest

from storage import (
    create_pool,
    get_character,
    get_pc_character,
    get_skill_value,
    update_san_current,
    upsert_character,
)

TEST_DSN = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(not TEST_DSN, reason="TEST_DATABASE_URL not set")


@pytest.fixture
def run_db():
    def _run(body):
        async def _main():
            pool = await create_pool(TEST_DSN)
            async with pool.acquire() as conn:
                await conn.execute(
                    "TRUNCATE registration_tokens, scenario_participants, characters, scenarios"
                )
            try:
                return await body(pool)
            finally:
                await pool.close()

        return asyncio.run(_main())

    return _run


SAMPLE_CHARACTER = {
    "name": "탐사자",
    "occupation": "사립탐정",
    "age": 32,
    "sex": "여",
    "residence": "서울",
    "birthplace": "부산",
    "str": 50,
    "dex": 60,
    "pow": 55,
    "con": 65,
    "app": 45,
    "edu": 70,
    "siz": 50,
    "int": 80,
    "mov": 8,
    "hp_current": None,
    "hp_max": None,
    "san_current": None,
    "san_starting": None,
    "mp_current": None,
    "mp_max": None,
    "damage_bonus": None,
    "build": None,
    "cash": None,
    "assets": None,
    "skills": {"회계": 5, "심리학": 10},
}


def test_get_character_returns_none_when_absent(run_db):
    async def _body(pool):
        assert await get_character(pool, guild_id=1, user_id=100) is None

    run_db(_body)


def test_upsert_then_get_roundtrips(run_db):
    async def _body(pool):
        await upsert_character(pool, guild_id=1, user_id=100, data=SAMPLE_CHARACTER)
        result = await get_character(pool, guild_id=1, user_id=100)
        assert result["name"] == "탐사자"
        assert result["int"] == 80
        assert result["skills"] == {"회계": 5, "심리학": 10}

    run_db(_body)


def test_upsert_stores_player(run_db):
    async def _body(pool):
        await upsert_character(
            pool, guild_id=1, user_id=100, data=dict(SAMPLE_CHARACTER, player="샬럿")
        )
        result = await get_character(pool, guild_id=1, user_id=100)
        assert result["player"] == "샬럿"

    run_db(_body)


def test_upsert_stores_manual_status_flags(run_db):
    async def _body(pool):
        await upsert_character(
            pool,
            guild_id=1,
            user_id=100,
            data=dict(SAMPLE_CHARACTER, major_wound=True, mp_depleted=True),
        )
        result = await get_character(pool, guild_id=1, user_id=100)
        assert result["major_wound"] is True
        assert result["mp_depleted"] is True

    run_db(_body)


def test_upsert_defaults_status_flags_to_false(run_db):
    async def _body(pool):
        await upsert_character(pool, guild_id=1, user_id=100, data=SAMPLE_CHARACTER)
        result = await get_character(pool, guild_id=1, user_id=100)
        assert result["major_wound"] is False
        assert result["mp_depleted"] is False
        assert result["temp_insanity"] is False
        assert result["indefinite_insanity"] is False

    run_db(_body)


def test_update_san_current_writes_insanity_flags(run_db):
    async def _body(pool):
        await upsert_character(pool, guild_id=1, user_id=100, data=SAMPLE_CHARACTER)
        await update_san_current(
            pool,
            guild_id=1,
            user_id=100,
            new_san=40,
            temp_insanity=True,
            indefinite_insanity=True,
        )
        result = await get_pc_character(pool, guild_id=1, user_id=100)
        assert result["temp_insanity"] is True
        assert result["indefinite_insanity"] is True

    run_db(_body)


def test_update_san_current_latches_insanity_flags(run_db):
    async def _body(pool):
        await upsert_character(pool, guild_id=1, user_id=100, data=SAMPLE_CHARACTER)
        await update_san_current(
            pool, guild_id=1, user_id=100, new_san=40, temp_insanity=True
        )
        # 이후 손실이 작아 이번엔 광기 조건을 만족하지 않아도 기존 상태는 유지된다.
        await update_san_current(
            pool, guild_id=1, user_id=100, new_san=39, temp_insanity=False
        )
        result = await get_pc_character(pool, guild_id=1, user_id=100)
        assert result["temp_insanity"] is True

    run_db(_body)


def test_upsert_roundtrips_weapons(run_db):
    async def _body(pool):
        weapons = [
            {
                "name": "권총 .38",
                "skill": "권총",
                "damage": "1d10",
                "range": "15m",
                "attacks": "1(3)",
                "ammo": "6",
                "malfunction": "100",
            }
        ]
        await upsert_character(
            pool, guild_id=1, user_id=100, data=dict(SAMPLE_CHARACTER, weapons=weapons)
        )
        result = await get_character(pool, guild_id=1, user_id=100)
        assert result["weapons"] == weapons

    run_db(_body)


def test_upsert_defaults_weapons_to_empty_list(run_db):
    async def _body(pool):
        await upsert_character(pool, guild_id=1, user_id=100, data=SAMPLE_CHARACTER)
        result = await get_character(pool, guild_id=1, user_id=100)
        assert result["weapons"] == []

    run_db(_body)


def test_upsert_roundtrips_bio(run_db):
    async def _body(pool):
        bio = {"gear": "트렌치코트, 손전등", "traits": "겁이 없다"}
        await upsert_character(
            pool, guild_id=1, user_id=100, data=dict(SAMPLE_CHARACTER, bio=bio)
        )
        result = await get_character(pool, guild_id=1, user_id=100)
        assert result["bio"] == bio

    run_db(_body)


def test_upsert_defaults_bio_to_empty_dict(run_db):
    async def _body(pool):
        await upsert_character(pool, guild_id=1, user_id=100, data=SAMPLE_CHARACTER)
        result = await get_character(pool, guild_id=1, user_id=100)
        assert result["bio"] == {}

    run_db(_body)


def test_upsert_overwrites_existing(run_db):
    async def _body(pool):
        await upsert_character(pool, guild_id=1, user_id=100, data=SAMPLE_CHARACTER)
        updated = dict(SAMPLE_CHARACTER, name="개명한탐사자")
        await upsert_character(pool, guild_id=1, user_id=100, data=updated)
        result = await get_character(pool, guild_id=1, user_id=100)
        assert result["name"] == "개명한탐사자"

    run_db(_body)


def test_characters_scoped_by_guild(run_db):
    async def _body(pool):
        await upsert_character(pool, guild_id=1, user_id=100, data=SAMPLE_CHARACTER)
        assert await get_character(pool, guild_id=2, user_id=100) is None

    run_db(_body)


def test_get_skill_value_returns_value_when_present(run_db):
    async def _body(pool):
        await upsert_character(pool, guild_id=1, user_id=100, data=SAMPLE_CHARACTER)
        assert await get_skill_value(pool, guild_id=1, user_id=100, skill_name="회계") == 5

    run_db(_body)


def test_get_skill_value_returns_none_when_character_missing(run_db):
    async def _body(pool):
        assert await get_skill_value(pool, guild_id=1, user_id=999, skill_name="회계") is None

    run_db(_body)


def test_get_skill_value_returns_none_when_skill_not_recorded(run_db):
    async def _body(pool):
        await upsert_character(pool, guild_id=1, user_id=100, data=SAMPLE_CHARACTER)
        assert await get_skill_value(pool, guild_id=1, user_id=100, skill_name="항법") is None

    run_db(_body)


def test_upsert_defaults_to_pc_role(run_db):
    async def _body(pool):
        await upsert_character(pool, guild_id=1, user_id=100, data=SAMPLE_CHARACTER)
        result = await get_character(pool, guild_id=1, user_id=100)
        assert result["role"] == "PC"
        assert result["scenario_id"] is None

    run_db(_body)


def test_upsert_npc_requires_scenario_and_allows_multiple_per_guild(run_db):
    async def _body(pool):
        from storage import create_scenario

        scenario_id = await create_scenario(
            pool, guild_id=1, title="시나리오", keeper_user_id=1, doc_url="https://x", structure=[]
        )
        npc_data = dict(SAMPLE_CHARACTER, name="관리인")
        await upsert_character(
            pool, guild_id=1, user_id=1, data=npc_data, role="NPC", scenario_id=scenario_id
        )
        another_npc = dict(SAMPLE_CHARACTER, name="건물주")
        await upsert_character(
            pool, guild_id=1, user_id=1, data=another_npc, role="NPC", scenario_id=scenario_id
        )
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT name FROM characters WHERE scenario_id = $1 ORDER BY name", scenario_id
            )
        assert [r["name"] for r in rows] == ["건물주", "관리인"]

    run_db(_body)


def test_upsert_npc_same_name_same_scenario_overwrites(run_db):
    async def _body(pool):
        from storage import create_scenario

        scenario_id = await create_scenario(
            pool, guild_id=1, title="시나리오", keeper_user_id=1, doc_url="https://x", structure=[]
        )
        data_v1 = dict(SAMPLE_CHARACTER, name="관리인", edu=50)
        await upsert_character(
            pool, guild_id=1, user_id=1, data=data_v1, role="NPC", scenario_id=scenario_id
        )
        data_v2 = dict(SAMPLE_CHARACTER, name="관리인", edu=70)
        await upsert_character(
            pool, guild_id=1, user_id=1, data=data_v2, role="NPC", scenario_id=scenario_id
        )
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT edu FROM characters WHERE scenario_id = $1 AND name = '관리인'", scenario_id
            )
        assert [r["edu"] for r in rows] == [70]

    run_db(_body)


def test_pc_and_npc_with_same_name_coexist(run_db):
    async def _body(pool):
        from storage import create_scenario

        scenario_id = await create_scenario(
            pool, guild_id=1, title="시나리오", keeper_user_id=1, doc_url="https://x", structure=[]
        )
        await upsert_character(pool, guild_id=1, user_id=100, data=SAMPLE_CHARACTER)
        npc_data = dict(SAMPLE_CHARACTER, name="탐사자")
        await upsert_character(
            pool, guild_id=1, user_id=1, data=npc_data, role="NPC", scenario_id=scenario_id
        )

        pc = await get_character(pool, guild_id=1, user_id=100)
        assert pc["role"] == "PC"
        async with pool.acquire() as conn:
            npc_row = await conn.fetchrow(
                "SELECT * FROM characters WHERE scenario_id = $1 AND role = 'NPC'", scenario_id
            )
        assert npc_row["name"] == "탐사자"

    run_db(_body)


def test_get_pc_character_ignores_npc_with_same_owner(run_db):
    async def _body(pool):
        from storage import create_scenario

        scenario_id = await create_scenario(
            pool, guild_id=1, title="시나리오", keeper_user_id=1, doc_url="https://x", structure=[]
        )
        npc_data = dict(SAMPLE_CHARACTER, name="관리인")
        await upsert_character(
            pool, guild_id=1, user_id=1, data=npc_data, role="NPC", scenario_id=scenario_id
        )
        assert await get_pc_character(pool, guild_id=1, user_id=1) is None

    run_db(_body)


def test_get_pc_character_returns_pc(run_db):
    async def _body(pool):
        await upsert_character(pool, guild_id=1, user_id=100, data=SAMPLE_CHARACTER)
        result = await get_pc_character(pool, guild_id=1, user_id=100)
        assert result["name"] == "탐사자"
        assert result["is_retired"] is False

    run_db(_body)


def test_update_san_current_updates_value(run_db):
    async def _body(pool):
        await upsert_character(pool, guild_id=1, user_id=100, data=SAMPLE_CHARACTER)
        assert await update_san_current(pool, guild_id=1, user_id=100, new_san=30) is True
        result = await get_pc_character(pool, guild_id=1, user_id=100)
        assert result["san_current"] == 30
        assert result["is_retired"] is False

    run_db(_body)


def test_update_san_current_zero_marks_retired(run_db):
    async def _body(pool):
        await upsert_character(pool, guild_id=1, user_id=100, data=SAMPLE_CHARACTER)
        await update_san_current(pool, guild_id=1, user_id=100, new_san=0)
        result = await get_pc_character(pool, guild_id=1, user_id=100)
        assert result["san_current"] == 0
        assert result["is_retired"] is True

    run_db(_body)


def test_update_san_current_returns_false_when_no_pc(run_db):
    async def _body(pool):
        assert await update_san_current(pool, guild_id=1, user_id=999, new_san=10) is False

    run_db(_body)
