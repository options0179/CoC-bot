import asyncio

import pytest

from storage import (
    create_pool,
    get_character,
    get_pc_character,
    get_skill_value,
    resolve_sanity_check,
    upsert_character,
)

@pytest.fixture
def run_db(tmp_path):
    def _run(body):
        async def _main():
            pool = await create_pool(str(tmp_path / "characters.sqlite3"))
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


def test_upsert_overwrites_existing(run_db):
    async def _body(pool):
        await upsert_character(pool, guild_id=1, user_id=100, data=SAMPLE_CHARACTER)
        updated = dict(SAMPLE_CHARACTER, name="개명한탐사자")
        await upsert_character(pool, guild_id=1, user_id=100, data=updated)
        result = await get_character(pool, guild_id=1, user_id=100)
        assert result["name"] == "개명한탐사자"

    run_db(_body)


def test_reregister_preserves_current_resources(run_db):
    async def _body(pool):
        original = dict(
            SAMPLE_CHARACTER,
            hp_current=20,
            hp_max=20,
            mp_current=11,
            mp_max=11,
            san_current=55,
            san_starting=55,
        )
        await upsert_character(pool, guild_id=1, user_id=100, data=original)
        async with pool.acquire() as conn:
            await conn.execute(
                """UPDATE characters SET hp_current = 12, mp_current = 4, san_current = 31
                WHERE guild_id = 1 AND discord_user_id = 100"""
            )

        sheet_update = dict(
            original,
            name="개명한탐사자",
            hp_current=24,
            hp_max=24,
            mp_current=12,
            mp_max=12,
            san_current=60,
            san_starting=60,
        )
        await upsert_character(pool, guild_id=1, user_id=100, data=sheet_update)

        result = await get_character(pool, guild_id=1, user_id=100)
        assert result["name"] == "개명한탐사자"
        assert (result["hp_current"], result["mp_current"], result["san_current"]) == (12, 4, 31)
        assert (result["hp_max"], result["mp_max"], result["san_starting"]) == (24, 12, 60)

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


def test_get_skill_value_uses_pc_when_owner_also_has_npc(run_db):
    async def _body(pool):
        from storage import create_scenario

        scenario_id = await create_scenario(
            pool, guild_id=1, title="시나리오", keeper_user_id=100, doc_url="https://x", structure=[]
        )
        await upsert_character(pool, guild_id=1, user_id=100, data=SAMPLE_CHARACTER)
        npc = dict(SAMPLE_CHARACTER, name="NPC", skills={"회계": 90})
        await upsert_character(pool, guild_id=1, user_id=100, data=npc, role="NPC", scenario_id=scenario_id)
        assert await get_skill_value(pool, 1, 100, "회계") == 5

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


def test_resolve_sanity_check_serializes_and_persists_both_losses(run_db):
    async def _body(pool):
        await upsert_character(
            pool,
            guild_id=1,
            user_id=100,
            data=dict(SAMPLE_CHARACTER, san_current=50, san_starting=50),
        )
        results = await asyncio.gather(
            resolve_sanity_check(pool, 1, 100, "1/1"),
            resolve_sanity_check(pool, 1, 100, "1/1"),
        )
        assert [status for status, _ in results] == ["ok", "ok"]
        result = await get_pc_character(pool, guild_id=1, user_id=100)
        assert result["san_current"] == 48
        assert result["is_retired"] is False

    run_db(_body)
