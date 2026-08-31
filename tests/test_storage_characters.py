import asyncio
import os

import pytest

from storage import create_pool, get_character, upsert_character

TEST_DSN = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(not TEST_DSN, reason="TEST_DATABASE_URL not set")


@pytest.fixture
def pool():
    async def _setup():
        p = await create_pool(TEST_DSN)
        async with p.acquire() as conn:
            await conn.execute("TRUNCATE guild_settings, characters")
        return p

    p = asyncio.run(_setup())
    yield p
    asyncio.run(p.close())


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


def test_get_character_returns_none_when_absent(pool):
    assert asyncio.run(get_character(pool, guild_id=1, user_id=100)) is None


def test_upsert_then_get_roundtrips(pool):
    asyncio.run(upsert_character(pool, guild_id=1, user_id=100, data=SAMPLE_CHARACTER))
    result = asyncio.run(get_character(pool, guild_id=1, user_id=100))
    assert result["name"] == "탐사자"
    assert result["int"] == 80
    assert result["skills"] == {"회계": 5, "심리학": 10}


def test_upsert_overwrites_existing(pool):
    asyncio.run(upsert_character(pool, guild_id=1, user_id=100, data=SAMPLE_CHARACTER))
    updated = dict(SAMPLE_CHARACTER, name="개명한탐사자")
    asyncio.run(upsert_character(pool, guild_id=1, user_id=100, data=updated))
    result = asyncio.run(get_character(pool, guild_id=1, user_id=100))
    assert result["name"] == "개명한탐사자"


def test_characters_scoped_by_guild(pool):
    asyncio.run(upsert_character(pool, guild_id=1, user_id=100, data=SAMPLE_CHARACTER))
    assert asyncio.run(get_character(pool, guild_id=2, user_id=100)) is None
