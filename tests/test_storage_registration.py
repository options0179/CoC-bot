import asyncio
import os

import pytest

from storage import close_registration, create_pool, is_registration_open, open_registration

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


def test_open_registration_succeeds_when_closed(pool):
    result = asyncio.run(open_registration(pool, guild_id=1, user_id=100))
    assert result is True
    assert asyncio.run(is_registration_open(pool, guild_id=1)) is True


def test_open_registration_fails_when_already_open_by_other(pool):
    asyncio.run(open_registration(pool, guild_id=1, user_id=100))
    result = asyncio.run(open_registration(pool, guild_id=1, user_id=200))
    assert result is False


def test_close_registration_fails_for_non_opener(pool):
    asyncio.run(open_registration(pool, guild_id=1, user_id=100))
    result = asyncio.run(close_registration(pool, guild_id=1, user_id=200))
    assert result is False
    assert asyncio.run(is_registration_open(pool, guild_id=1)) is True


def test_close_registration_succeeds_for_opener(pool):
    asyncio.run(open_registration(pool, guild_id=1, user_id=100))
    result = asyncio.run(close_registration(pool, guild_id=1, user_id=100))
    assert result is True
    assert asyncio.run(is_registration_open(pool, guild_id=1)) is False


def test_is_registration_open_false_for_unknown_guild(pool):
    assert asyncio.run(is_registration_open(pool, guild_id=999)) is False
