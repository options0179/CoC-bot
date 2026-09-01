import asyncpg
import json

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


_CHARACTER_COLUMNS = [
    "name", "occupation", "age", "sex", "residence", "birthplace",
    "str", "dex", "pow", "con", "app", "edu", "siz", "int", "mov",
    "hp_current", "hp_max", "san_current", "san_starting",
    "mp_current", "mp_max", "damage_bonus", "build", "cash", "assets", "skills",
]


def _quote(column: str) -> str:
    return f'"{column}"' if column == "int" else column


async def upsert_character(pool: asyncpg.Pool, guild_id: int, user_id: int, data: dict) -> None:
    values = [data.get(col) for col in _CHARACTER_COLUMNS]
    skills_index = _CHARACTER_COLUMNS.index("skills")
    values[skills_index] = json.dumps(values[skills_index] or {})

    quoted = [_quote(c) for c in _CHARACTER_COLUMNS]
    placeholders = ", ".join(f"${i + 3}" for i in range(len(_CHARACTER_COLUMNS)))
    update_clause = ", ".join(f"{qc} = EXCLUDED.{qc}" for qc in quoted)
    query = f"""
        INSERT INTO characters (guild_id, discord_user_id, {", ".join(quoted)}, updated_at)
        VALUES ($1, $2, {placeholders}, now())
        ON CONFLICT (guild_id, discord_user_id)
        DO UPDATE SET {update_clause}, updated_at = now()
    """
    async with pool.acquire() as conn:
        await conn.execute(query, guild_id, user_id, *values)


async def get_character(pool: asyncpg.Pool, guild_id: int, user_id: int) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM characters WHERE guild_id = $1 AND discord_user_id = $2",
            guild_id,
            user_id,
        )
    if row is None:
        return None
    result = dict(row)
    if isinstance(result["skills"], str):
        result["skills"] = json.loads(result["skills"])
    return result


async def get_skill_value(
    pool: asyncpg.Pool, guild_id: int, user_id: int, skill_name: str
) -> int | None:
    character = await get_character(pool, guild_id, user_id)
    if character is None:
        return None
    return character["skills"].get(skill_name)
