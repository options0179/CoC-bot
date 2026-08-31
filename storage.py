import asyncpg

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id BIGINT PRIMARY KEY,
    registration_open BOOLEAN NOT NULL DEFAULT false,
    opened_by BIGINT
);

CREATE TABLE IF NOT EXISTS characters (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    discord_user_id BIGINT NOT NULL,
    name TEXT,
    occupation TEXT,
    age INTEGER,
    sex TEXT,
    residence TEXT,
    birthplace TEXT,
    str INTEGER,
    dex INTEGER,
    pow INTEGER,
    con INTEGER,
    app INTEGER,
    edu INTEGER,
    siz INTEGER,
    "int" INTEGER,
    mov INTEGER,
    hp_current INTEGER,
    hp_max INTEGER,
    san_current INTEGER,
    san_starting INTEGER,
    mp_current INTEGER,
    mp_max INTEGER,
    damage_bonus TEXT,
    build TEXT,
    cash INTEGER,
    assets INTEGER,
    skills JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (guild_id, discord_user_id)
);
"""


async def create_pool(dsn: str) -> asyncpg.Pool:
    pool = await asyncpg.create_pool(dsn)
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
    return pool


async def open_registration(pool: asyncpg.Pool, guild_id: int, user_id: int) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT registration_open FROM guild_settings WHERE guild_id = $1", guild_id
        )
        if row and row["registration_open"]:
            return False
        await conn.execute(
            """
            INSERT INTO guild_settings (guild_id, registration_open, opened_by)
            VALUES ($1, true, $2)
            ON CONFLICT (guild_id) DO UPDATE SET registration_open = true, opened_by = $2
            """,
            guild_id,
            user_id,
        )
        return True


async def close_registration(pool: asyncpg.Pool, guild_id: int, user_id: int) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT registration_open, opened_by FROM guild_settings WHERE guild_id = $1",
            guild_id,
        )
        if not row or not row["registration_open"] or row["opened_by"] != user_id:
            return False
        await conn.execute(
            "UPDATE guild_settings SET registration_open = false, opened_by = NULL "
            "WHERE guild_id = $1",
            guild_id,
        )
        return True


async def is_registration_open(pool: asyncpg.Pool, guild_id: int) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT registration_open FROM guild_settings WHERE guild_id = $1", guild_id
        )
        return bool(row and row["registration_open"])
