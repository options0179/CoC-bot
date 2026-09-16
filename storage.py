import asyncpg
import json
import secrets
from datetime import datetime, timedelta, timezone

SCHEMA_SQL = """
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

ALTER TABLE characters ADD COLUMN IF NOT EXISTS player TEXT;
ALTER TABLE characters ADD COLUMN IF NOT EXISTS weapons JSONB NOT NULL DEFAULT '[]';
ALTER TABLE characters ADD COLUMN IF NOT EXISTS major_wound BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE characters ADD COLUMN IF NOT EXISTS mp_depleted BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE characters ADD COLUMN IF NOT EXISTS temp_insanity BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE characters ADD COLUMN IF NOT EXISTS indefinite_insanity BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE characters ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'PC';
ALTER TABLE characters ADD COLUMN IF NOT EXISTS scenario_id INTEGER REFERENCES scenarios(id);
ALTER TABLE characters ADD COLUMN IF NOT EXISTS is_retired BOOLEAN NOT NULL DEFAULT false;
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

CREATE TABLE IF NOT EXISTS registration_tokens (
    token TEXT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    discord_user_id BIGINT NOT NULL,
    role TEXT NOT NULL DEFAULT 'PC',
    scenario_id INTEGER REFERENCES scenarios(id),
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ
);

ALTER TABLE registration_tokens ADD COLUMN IF NOT EXISTS player_name TEXT;
"""


async def create_pool(dsn: str) -> asyncpg.Pool:
    pool = await asyncpg.create_pool(dsn)
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
    return pool


_CHARACTER_COLUMNS = [
    "name", "player", "occupation", "age", "sex", "residence", "birthplace",
    "str", "dex", "pow", "con", "app", "edu", "siz", "int", "mov",
    "hp_current", "hp_max", "san_current", "san_starting",
    "mp_current", "mp_max", "damage_bonus", "build", "cash", "assets", "skills",
    "weapons", "major_wound", "mp_depleted",
]

# JSONB 컬럼: 값이 없으면 빈 컨테이너로 채워 직렬화한다.
_JSON_COLUMNS = {"skills": dict, "weapons": list}

# NOT NULL 컬럼이라 값이 없으면 NULL 대신 false로 채워 넣는다.
_BOOL_COLUMNS = ("major_wound", "mp_depleted")


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
    for column, empty in _JSON_COLUMNS.items():
        index = _CHARACTER_COLUMNS.index(column)
        values[index] = json.dumps(values[index] if values[index] else empty())
    for column in _BOOL_COLUMNS:
        index = _CHARACTER_COLUMNS.index(column)
        values[index] = bool(values[index])

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


def _row_to_character(row) -> dict | None:
    if row is None:
        return None
    result = dict(row)
    for column in _JSON_COLUMNS:
        if isinstance(result.get(column), str):
            result[column] = json.loads(result[column])
    return result


async def get_character(pool: asyncpg.Pool, guild_id: int, user_id: int) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM characters WHERE guild_id = $1 AND discord_user_id = $2",
            guild_id,
            user_id,
        )
    return _row_to_character(row)


async def get_pc_character(pool: asyncpg.Pool, guild_id: int, user_id: int) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM characters WHERE guild_id = $1 AND discord_user_id = $2 AND role = 'PC'",
            guild_id,
            user_id,
        )
    return _row_to_character(row)


async def update_san_current(
    pool: asyncpg.Pool,
    guild_id: int,
    user_id: int,
    new_san: int,
    temp_insanity: bool = False,
    indefinite_insanity: bool = False,
) -> bool:
    # 광기 상태는 한 번 발생하면 유지된다(OR). 이후 굴림이 조건을 만족하지 않는다고
    # 해서 이미 걸린 광기가 풀리지는 않으므로, 해제는 키퍼 재량(직접 DB/재등록)에 맡긴다.
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE characters
            SET san_current = $1,
                is_retired = $2,
                temp_insanity = temp_insanity OR $3,
                indefinite_insanity = indefinite_insanity OR $4,
                updated_at = now()
            WHERE guild_id = $5 AND discord_user_id = $6 AND role = 'PC'
            """,
            new_san,
            new_san == 0,
            temp_insanity,
            indefinite_insanity,
            guild_id,
            user_id,
        )
    return result == "UPDATE 1"


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
    return [_row_to_character(row) for row in rows]


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


_TOKEN_TTL = timedelta(minutes=30)


# ponytail: KPC/NPC tokens need a real scenario_id — NULL scenario_id + role
# in ('KPC','NPC') means the character upsert's (scenario_id, name) conflict
# target never matches, so every submission inserts a duplicate row instead
# of upserting. Phase 3 (which issues these tokens) must always pass a real
# scenario_id for KPC/NPC roles.
async def create_registration_token(
    pool: asyncpg.Pool,
    guild_id: int,
    user_id: int,
    role: str = "PC",
    scenario_id: int | None = None,
    player_name: str | None = None,
) -> str:
    token = secrets.token_urlsafe(24)
    expires_at = datetime.now(timezone.utc) + _TOKEN_TTL
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO registration_tokens
                (token, guild_id, discord_user_id, role, scenario_id, expires_at, player_name)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            token,
            guild_id,
            user_id,
            role,
            scenario_id,
            expires_at,
            player_name,
        )
    return token


async def get_valid_registration_token(pool: asyncpg.Pool, token: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM registration_tokens
            WHERE token = $1 AND used_at IS NULL AND expires_at > now()
            """,
            token,
        )
    return dict(row) if row else None


async def consume_registration_token(pool: asyncpg.Pool, token: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE registration_tokens SET used_at = now() WHERE token = $1", token
        )
