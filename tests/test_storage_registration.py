import asyncio
import os

import pytest

from storage import close_registration, create_pool, is_registration_open, open_registration

TEST_DSN = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(not TEST_DSN, reason="TEST_DATABASE_URL not set")


@pytest.fixture
def run_db():
    def _run(body):
        async def _main():
            pool = await create_pool(TEST_DSN)
            async with pool.acquire() as conn:
                await conn.execute("TRUNCATE guild_settings, characters")
            try:
                return await body(pool)
            finally:
                await pool.close()

        return asyncio.run(_main())

    return _run


def test_open_registration_succeeds_when_closed(run_db):
    async def _body(pool):
        result = await open_registration(pool, guild_id=1, user_id=100)
        assert result is True
        assert await is_registration_open(pool, guild_id=1) is True

    run_db(_body)


def test_open_registration_fails_when_already_open_by_other(run_db):
    async def _body(pool):
        await open_registration(pool, guild_id=1, user_id=100)
        result = await open_registration(pool, guild_id=1, user_id=200)
        assert result is False

    run_db(_body)


def test_close_registration_fails_for_non_opener(run_db):
    async def _body(pool):
        await open_registration(pool, guild_id=1, user_id=100)
        result = await close_registration(pool, guild_id=1, user_id=200)
        assert result is False
        assert await is_registration_open(pool, guild_id=1) is True

    run_db(_body)


def test_close_registration_succeeds_for_opener(run_db):
    async def _body(pool):
        await open_registration(pool, guild_id=1, user_id=100)
        result = await close_registration(pool, guild_id=1, user_id=100)
        assert result is True
        assert await is_registration_open(pool, guild_id=1) is False

    run_db(_body)


def test_is_registration_open_false_for_unknown_guild(run_db):
    async def _body(pool):
        assert await is_registration_open(pool, guild_id=999) is False

    run_db(_body)
