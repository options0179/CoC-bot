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

CREATE TABLE IF NOT EXISTS scenarios (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    title TEXT NOT NULL,
    keeper_user_id BIGINT NOT NULL,
    doc_url TEXT NOT NULL,
    structure JSONB NOT NULL,
    channel_id BIGINT,
    current_scene_index INTEGER NOT NULL DEFAULT 0,
    current_line_index INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (guild_id, title),
    UNIQUE (channel_id)
);

ALTER TABLE characters ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'PC';
ALTER TABLE characters ADD COLUMN IF NOT EXISTS scenario_id INTEGER REFERENCES scenarios(id);
ALTER TABLE characters DROP CONSTRAINT IF EXISTS characters_guild_id_discord_user_id_key;
CREATE UNIQUE INDEX IF NOT EXISTS ux_characters_pc
    ON characters (guild_id, discord_user_id) WHERE role = 'PC';
CREATE UNIQUE INDEX IF NOT EXISTS ux_characters_npc_kpc
    ON characters (scenario_id, name) WHERE role IN ('KPC', 'NPC');

CREATE TABLE IF NOT EXISTS scenario_participants (
    scenario_id INTEGER NOT NULL REFERENCES scenarios(id),
    character_id INTEGER NOT NULL REFERENCES characters(id),
    PRIMARY KEY (scenario_id, character_id)
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


async def upsert_character(
    pool: asyncpg.Pool,
    guild_id: int,
    user_id: int,
    data: dict,
    role: str = "PC",
    scenario_id: int | None = None,
) -> None:
    values = [data.get(col) for col in _CHARACTER_COLUMNS]
    skills_index = _CHARACTER_COLUMNS.index("skills")
    values[skills_index] = json.dumps(values[skills_index] or {})

    quoted = [_quote(c) for c in _CHARACTER_COLUMNS]
    placeholders = ", ".join(f"${i + 5}" for i in range(len(_CHARACTER_COLUMNS)))
    update_clause = ", ".join(f"{qc} = EXCLUDED.{qc}" for qc in quoted)
    conflict = (
        "(guild_id, discord_user_id) WHERE role = 'PC'"
        if role == "PC"
        else "(scenario_id, name) WHERE role IN ('KPC', 'NPC')"
    )
    query = f"""
        INSERT INTO characters (guild_id, discord_user_id, role, scenario_id, {", ".join(quoted)}, updated_at)
        VALUES ($1, $2, $3, $4, {placeholders}, now())
        ON CONFLICT {conflict}
        DO UPDATE SET {update_clause}, updated_at = now()
    """
    async with pool.acquire() as conn:
        await conn.execute(query, guild_id, user_id, role, scenario_id, *values)


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


def _scenario_row_to_dict(row) -> dict | None:
    if row is None:
        return None
    result = dict(row)
    if isinstance(result["structure"], str):
        result["structure"] = json.loads(result["structure"])
    return result


async def create_scenario(
    pool: asyncpg.Pool,
    guild_id: int,
    title: str,
    keeper_user_id: int,
    doc_url: str,
    structure: list,
) -> int:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO scenarios (guild_id, title, keeper_user_id, doc_url, structure)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
            """,
            guild_id,
            title,
            keeper_user_id,
            doc_url,
            json.dumps(structure),
        )
        return row["id"]


async def get_scenario_by_title(pool: asyncpg.Pool, guild_id: int, title: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM scenarios WHERE guild_id = $1 AND title = $2", guild_id, title
        )
    return _scenario_row_to_dict(row)


async def get_scenario_by_channel(pool: asyncpg.Pool, channel_id: int) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM scenarios WHERE channel_id = $1", channel_id)
    return _scenario_row_to_dict(row)


async def bind_scenario_channel(
    pool: asyncpg.Pool, guild_id: int, title: str, channel_id: int
) -> bool:
    async with pool.acquire() as conn:
        try:
            result = await conn.execute(
                "UPDATE scenarios SET channel_id = $1 WHERE guild_id = $2 AND title = $3",
                channel_id,
                guild_id,
                title,
            )
        except asyncpg.UniqueViolationError:
            return False
    return result == "UPDATE 1"


async def join_scenario(pool: asyncpg.Pool, scenario_id: int, character_id: int) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO scenario_participants (scenario_id, character_id)
            VALUES ($1, $2)
            ON CONFLICT DO NOTHING
            """,
            scenario_id,
            character_id,
        )


async def get_roster(pool: asyncpg.Pool, scenario_id: int) -> list[dict]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT c.* FROM characters c
            JOIN scenario_participants sp ON sp.character_id = c.id
            WHERE sp.scenario_id = $1
            ORDER BY c.name
            """,
            scenario_id,
        )
    results = []
    for row in rows:
        character = dict(row)
        if isinstance(character["skills"], str):
            character["skills"] = json.loads(character["skills"])
        results.append(character)
    return results


async def advance_narration_position(
    pool: asyncpg.Pool, scenario_id: int, scene_index: int, line_index: int
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE scenarios SET current_scene_index = $1, current_line_index = $2 WHERE id = $3",
            scene_index,
            line_index,
            scenario_id,
        )
