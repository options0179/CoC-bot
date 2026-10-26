import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from storage import (
    create_scenario,
    consume_registration_token,
    create_pool,
    create_registration_token,
    get_valid_registration_token,
)


@pytest.fixture
def run_db(tmp_path):
    def _run(body):
        async def _main():
            pool = await create_pool(str(tmp_path / "tokens.sqlite3"))
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


def test_create_token_stores_role_scenario_and_player_name(run_db):
    async def _body(pool):
        scenario_id = await create_scenario(
            pool, guild_id=1, title="테스트", keeper_user_id=100, doc_url="https://example.com", structure=[]
        )
        token = await create_registration_token(
            pool, guild_id=1, user_id=100, role="KPC", scenario_id=scenario_id, player_name="샬럿"
        )
        row = await get_valid_registration_token(pool, token)
        assert row["role"] == "KPC"
        assert row["scenario_id"] == scenario_id
        assert row["player_name"] == "샬럿"

    run_db(_body)


def test_get_valid_token_returns_none_for_unknown_token(run_db):
    async def _body(pool):
        assert await get_valid_registration_token(pool, "unknown") is None

    run_db(_body)


def test_expired_token_is_not_valid(run_db):
    async def _body(pool):
        token = await create_registration_token(pool, guild_id=1, user_id=100)
        expires_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE registration_tokens SET expires_at = $1 WHERE token = $2",
                expires_at,
                token,
            )
        assert await get_valid_registration_token(pool, token) is None

    run_db(_body)


def test_consumed_token_is_no_longer_valid(run_db):
    async def _body(pool):
        token = await create_registration_token(pool, guild_id=1, user_id=100)
        await consume_registration_token(pool, token)
        assert await get_valid_registration_token(pool, token) is None

    run_db(_body)


def test_consuming_token_twice_is_harmless(run_db):
    async def _body(pool):
        token = await create_registration_token(pool, guild_id=1, user_id=100)
        await consume_registration_token(pool, token)
        await consume_registration_token(pool, token)
        assert await get_valid_registration_token(pool, token) is None

    run_db(_body)
