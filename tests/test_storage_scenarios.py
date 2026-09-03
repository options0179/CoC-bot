import asyncio
import os

import pytest

from storage import (
    bind_scenario_channel,
    create_scenario,
    get_character,
    get_roster,
    get_scenario_by_channel,
    get_scenario_by_title,
    join_scenario,
    upsert_character,
)

TEST_DSN = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DSN, reason="TEST_DATABASE_URL not set")


@pytest.fixture
def run_db():
    def _run(body):
        async def _main():
            from storage import create_pool

            pool = await create_pool(TEST_DSN)
            async with pool.acquire() as conn:
                await conn.execute(
                    "TRUNCATE scenario_participants, characters, scenarios, guild_settings"
                )
            try:
                return await body(pool)
            finally:
                await pool.close()

        return asyncio.run(_main())

    return _run


SAMPLE_STRUCTURE = [
    {"part": "제1부", "scene": "장면 1. 일상", "lines": ["늦은 오후입니다.", "문서가 남아있습니다."]}
]

SAMPLE_CHARACTER = {
    "name": "탐사자", "occupation": "탐정", "age": 30, "sex": "여",
    "residence": "서울", "birthplace": "부산",
    "str": 50, "dex": 50, "pow": 50, "con": 50, "app": 50,
    "edu": 50, "siz": 50, "int": 50, "mov": 8,
    "hp_current": None, "hp_max": None, "san_current": None, "san_starting": None,
    "mp_current": None, "mp_max": None, "damage_bonus": None, "build": None,
    "cash": None, "assets": None, "skills": {},
}


def test_create_then_get_by_title(run_db):
    async def _body(pool):
        await create_scenario(
            pool, guild_id=1, title="마지막 상영", keeper_user_id=999,
            doc_url="https://x", structure=SAMPLE_STRUCTURE,
        )
        scenario = await get_scenario_by_title(pool, guild_id=1, title="마지막 상영")
        assert scenario is not None
        assert scenario["keeper_user_id"] == 999
        assert scenario["structure"] == SAMPLE_STRUCTURE
        assert scenario["current_scene_index"] == 0
        assert scenario["current_line_index"] == 0
        assert scenario["channel_id"] is None

    run_db(_body)


def test_get_by_title_returns_none_when_absent(run_db):
    async def _body(pool):
        assert await get_scenario_by_title(pool, guild_id=1, title="없음") is None

    run_db(_body)


def test_duplicate_title_in_same_guild_raises(run_db):
    async def _body(pool):
        await create_scenario(
            pool, guild_id=1, title="중복", keeper_user_id=1,
            doc_url="https://x", structure=SAMPLE_STRUCTURE,
        )
        with pytest.raises(Exception):
            await create_scenario(
                pool, guild_id=1, title="중복", keeper_user_id=2,
                doc_url="https://y", structure=SAMPLE_STRUCTURE,
            )

    run_db(_body)


def test_bind_scenario_channel_succeeds_once(run_db):
    async def _body(pool):
        await create_scenario(
            pool, guild_id=1, title="시작", keeper_user_id=1,
            doc_url="https://x", structure=SAMPLE_STRUCTURE,
        )
        assert await bind_scenario_channel(pool, guild_id=1, title="시작", channel_id=555) is True
        scenario = await get_scenario_by_channel(pool, channel_id=555)
        assert scenario["title"] == "시작"

    run_db(_body)


def test_bind_scenario_channel_fails_when_channel_taken(run_db):
    async def _body(pool):
        await create_scenario(
            pool, guild_id=1, title="A", keeper_user_id=1, doc_url="https://x", structure=SAMPLE_STRUCTURE
        )
        await create_scenario(
            pool, guild_id=1, title="B", keeper_user_id=1, doc_url="https://y", structure=SAMPLE_STRUCTURE
        )
        assert await bind_scenario_channel(pool, guild_id=1, title="A", channel_id=1) is True
        assert await bind_scenario_channel(pool, guild_id=1, title="B", channel_id=1) is False

    run_db(_body)


def test_bind_scenario_channel_fails_when_scenario_missing(run_db):
    async def _body(pool):
        assert await bind_scenario_channel(pool, guild_id=1, title="없음", channel_id=1) is False

    run_db(_body)


def test_get_scenario_by_channel_returns_none_when_unbound(run_db):
    async def _body(pool):
        await create_scenario(
            pool, guild_id=1, title="A", keeper_user_id=1, doc_url="https://x", structure=SAMPLE_STRUCTURE
        )
        assert await get_scenario_by_channel(pool, channel_id=999) is None

    run_db(_body)


def test_join_scenario_adds_character_to_roster(run_db):
    async def _body(pool):
        scenario_id = await create_scenario(
            pool, guild_id=1, title="시나리오", keeper_user_id=1, doc_url="https://x", structure=[]
        )
        await upsert_character(pool, guild_id=1, user_id=100, data=SAMPLE_CHARACTER)
        character = await get_character(pool, guild_id=1, user_id=100)
        await join_scenario(pool, scenario_id, character["id"])
        roster = await get_roster(pool, scenario_id)
        assert [c["name"] for c in roster] == ["탐사자"]

    run_db(_body)


def test_join_scenario_is_idempotent(run_db):
    async def _body(pool):
        scenario_id = await create_scenario(
            pool, guild_id=1, title="시나리오", keeper_user_id=1, doc_url="https://x", structure=[]
        )
        await upsert_character(pool, guild_id=1, user_id=100, data=SAMPLE_CHARACTER)
        character = await get_character(pool, guild_id=1, user_id=100)
        await join_scenario(pool, scenario_id, character["id"])
        await join_scenario(pool, scenario_id, character["id"])
        roster = await get_roster(pool, scenario_id)
        assert len(roster) == 1

    run_db(_body)


def test_get_roster_empty_when_no_participants(run_db):
    async def _body(pool):
        scenario_id = await create_scenario(
            pool, guild_id=1, title="시나리오", keeper_user_id=1, doc_url="https://x", structure=[]
        )
        assert await get_roster(pool, scenario_id) == []

    run_db(_body)
