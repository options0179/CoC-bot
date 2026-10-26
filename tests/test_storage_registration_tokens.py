import asyncio
import os

import pytest

from storage import (
    consume_registration_token,
    create_pool,
    create_registration_token,
    get_valid_registration_token,
)

TEST_DSN = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(not TEST_DSN, reason="TEST_DATABASE_URL not set")


@pytest.fixture
def run_db():
    def _run(body):
        async def _main():
            pool = await create_pool(TEST_DSN)
            async with pool.acquire() as conn:
                await conn.execute("TRUNCATE registration_tokens")
            try:
                return await body(pool)
            finally:
                await pool.close()

        return asyncio.run(_main())

    return _run


def test_create_then_get_valid_token(run_db):
    async def _body(pool):
        token = await create_registration_token(pool, guild_id=1, user_id=100)
        row = await get_valid_registration_token(pool, token)
        assert row["guild_id"] == 1
        assert row["discord_user_id"] == 100
        assert row["role"] == "PC"
        assert row["scenario_id"] is None

    run_db(_body)


def test_create_token_with_role_and_scenario(run_db):
    async def _body(pool):
        token = await create_registration_token(
            pool, guild_id=1, user_id=100, role="KPC", scenario_id=None
        )
        row = await get_valid_registration_token(pool, token)
        assert row["role"] == "KPC"

    run_db(_body)


def test_create_token_stores_player_name(run_db):
    async def _body(pool):
        token = await create_registration_token(
            pool, guild_id=1, user_id=100, player_name="샬럿"
        )
        row = await get_valid_registration_token(pool, token)
        assert row["player_name"] == "샬럿"

    run_db(_body)


def test_create_token_without_player_name_stores_null(run_db):
    async def _body(pool):
        token = await create_registration_token(pool, guild_id=1, user_id=100)
        row = await get_valid_registration_token(pool, token)
        assert row["player_name"] is None

    run_db(_body)


def test_get_valid_token_returns_none_for_unknown_token(run_db):
    async def _body(pool):
        row = await get_valid_registration_token(pool, "does-not-exist")
        assert row is None

    run_db(_body)


def test_expired_token_is_not_valid(run_db):
    async def _body(pool):
        token = await create_registration_token(pool, guild_id=1, user_id=100)
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE registration_tokens SET expires_at = now() - interval '1 minute' "
                "WHERE token = $1",
                token,
            )
        row = await get_valid_registration_token(pool, token)
        assert row is None

    run_db(_body)


def test_consumed_token_is_no_longer_valid(run_db):
    async def _body(pool):
        token = await create_registration_token(pool, guild_id=1, user_id=100)
        await consume_registration_token(pool, token)
        row = await get_valid_registration_token(pool, token)
        assert row is None

    run_db(_body)


def test_consuming_twice_is_harmless(run_db):
    async def _body(pool):
        token = await create_registration_token(pool, guild_id=1, user_id=100)
        await consume_registration_token(pool, token)
        await consume_registration_token(pool, token)  # 두 번째 호출도 예외 없이 통과해야 함
        row = await get_valid_registration_token(pool, token)
        assert row is None

    run_db(_body)
