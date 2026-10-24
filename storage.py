import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
import re
import sqlite3
from typing import Literal

from dice import SanityResult, sanity_check

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS scenarios (
    id INTEGER PRIMARY KEY,
    guild_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    keeper_user_id INTEGER NOT NULL,
    doc_url TEXT NOT NULL,
    structure TEXT NOT NULL,
    channel_id INTEGER,
    current_scene_index INTEGER NOT NULL DEFAULT 0,
    current_line_index INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (guild_id, title),
    UNIQUE (channel_id)
);

CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY,
    guild_id INTEGER NOT NULL,
    discord_user_id INTEGER NOT NULL,
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
    skills TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    role TEXT NOT NULL DEFAULT 'PC',
    scenario_id INTEGER REFERENCES scenarios(id),
    is_retired INTEGER NOT NULL DEFAULT 0
);

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


class SQLiteConnection:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    @staticmethod
    def _query(sql: str) -> str:
        return re.sub(r"\$\d+", "?", sql)

    async def execute(self, sql: str, *args) -> str:
        cursor = await asyncio.to_thread(self._connection.execute, self._query(sql), args)
        rowcount = cursor.rowcount
        await asyncio.to_thread(cursor.close)
        return f"UPDATE {rowcount}"

    async def fetchrow(self, sql: str, *args):
        cursor = await asyncio.to_thread(self._connection.execute, self._query(sql), args)
        row = await asyncio.to_thread(cursor.fetchone)
        await asyncio.to_thread(cursor.close)
        return row

    async def fetch(self, sql: str, *args):
        cursor = await asyncio.to_thread(self._connection.execute, self._query(sql), args)
        rows = await asyncio.to_thread(cursor.fetchall)
        await asyncio.to_thread(cursor.close)
        return rows

    async def fetchval(self, sql: str, *args):
        row = await self.fetchrow(sql, *args)
        return row[0] if row is not None else None

    @asynccontextmanager
    async def transaction(self):
        await asyncio.to_thread(self._connection.execute, "BEGIN IMMEDIATE")
        try:
            yield self
        except BaseException:
            await asyncio.to_thread(self._connection.rollback)
            raise
        else:
            await asyncio.to_thread(self._connection.commit)


class SQLitePool:
    """A single SQLite connection, serialized to keep async callers safe."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = SQLiteConnection(connection)
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire(self):
        async with self._lock:
            yield self._connection

    async def close(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self._connection._connection.close)


async def create_pool(path: str) -> SQLitePool:
    if path != ":memory:":
        Path(path).expanduser().parent.mkdir(parents=True, exist_ok=True)
    connection = await asyncio.to_thread(
        sqlite3.connect, str(Path(path).expanduser()) if path != ":memory:" else path,
        check_same_thread=False,
        timeout=30,
        isolation_level=None,
    )
    connection.row_factory = sqlite3.Row
    await asyncio.to_thread(connection.execute, "PRAGMA foreign_keys = ON")
    await asyncio.to_thread(connection.execute, "PRAGMA busy_timeout = 30000")
    await asyncio.to_thread(connection.execute, "PRAGMA journal_mode = WAL")
    await asyncio.to_thread(connection.executescript, SCHEMA_SQL)
    return SQLitePool(connection)


_CHARACTER_COLUMNS = [
    "name", "occupation", "age", "sex", "residence", "birthplace",
    "str", "dex", "pow", "con", "app", "edu", "siz", "int", "mov",
    "hp_current", "hp_max", "san_current", "san_starting",
    "mp_current", "mp_max", "damage_bonus", "build", "cash", "assets", "skills",
]


def _quote(column: str) -> str:
    return f'"{column}"' if column == "int" else column


async def _upsert_character(
    conn: SQLiteConnection,
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
    placeholders = ", ".join("?" for _ in _CHARACTER_COLUMNS)
    current_fields = {"hp_current", "mp_current", "san_current"}
    update_clause = ", ".join(
        f"{_quote(column)} = EXCLUDED.{_quote(column)}"
        for column in _CHARACTER_COLUMNS
        if column not in current_fields
    )
    update_clause += """
        , hp_current = MIN(COALESCE(characters.hp_current, EXCLUDED.hp_max), EXCLUDED.hp_max)
        , mp_current = MIN(COALESCE(characters.mp_current, EXCLUDED.mp_max), EXCLUDED.mp_max)
        , san_current = COALESCE(characters.san_current, EXCLUDED.san_current)
    """
    conflict = (
        "(guild_id, discord_user_id) WHERE role = 'PC'"
        if role == "PC"
        else "(scenario_id, name) WHERE role IN ('KPC', 'NPC')"
    )
    query = f"""
        INSERT INTO characters (guild_id, discord_user_id, role, scenario_id, {", ".join(quoted)}, updated_at)
        VALUES (?, ?, ?, ?, {placeholders}, CURRENT_TIMESTAMP)
        ON CONFLICT {conflict}
        DO UPDATE SET {update_clause}, updated_at = CURRENT_TIMESTAMP
    """
    await conn.execute(query, guild_id, user_id, role, scenario_id, *values)


async def upsert_character(
    pool: SQLitePool,
    guild_id: int,
    user_id: int,
    data: dict,
    role: str = "PC",
    scenario_id: int | None = None,
) -> None:
    async with pool.acquire() as conn:
        await _upsert_character(conn, guild_id, user_id, data, role, scenario_id)


def _row_to_character(row) -> dict | None:
    if row is None:
        return None
    result = dict(row)
    if isinstance(result["skills"], str):
        result["skills"] = json.loads(result["skills"])
    result["is_retired"] = bool(result["is_retired"])
    return result


async def get_character(pool: SQLitePool, guild_id: int, user_id: int) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM characters WHERE guild_id = $1 AND discord_user_id = $2",
            guild_id,
            user_id,
        )
    return _row_to_character(row)


async def get_pc_character(pool: SQLitePool, guild_id: int, user_id: int) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM characters WHERE guild_id = $1 AND discord_user_id = $2 AND role = 'PC'",
            guild_id,
            user_id,
        )
    return _row_to_character(row)


async def resolve_sanity_check(
    pool: SQLitePool, guild_id: int, user_id: int, formula: str
) -> tuple[Literal["missing", "retired", "incomplete", "ok"], SanityResult | None]:
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                SELECT san_current, is_retired FROM characters
                WHERE guild_id = $1 AND discord_user_id = $2 AND role = 'PC'
                """,
                guild_id,
                user_id,
            )
            if row is None:
                return "missing", None
            if row["is_retired"]:
                return "retired", None
            if row["san_current"] is None:
                return "incomplete", None

            result = sanity_check(row["san_current"], formula)
            await conn.execute(
                """
                UPDATE characters SET san_current = $1, is_retired = $2, updated_at = CURRENT_TIMESTAMP
                WHERE guild_id = $3 AND discord_user_id = $4 AND role = 'PC'
                """,
                result.remaining_san,
                int(result.remaining_san == 0),
                guild_id,
                user_id,
            )
    return "ok", result


async def get_skill_value(
    pool: SQLitePool, guild_id: int, user_id: int, skill_name: str
) -> int | None:
    character = await get_pc_character(pool, guild_id, user_id)
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
    pool: SQLitePool,
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


async def get_scenario_by_title(pool: SQLitePool, guild_id: int, title: str) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM scenarios WHERE guild_id = $1 AND title = $2", guild_id, title
        )
    return _scenario_row_to_dict(row)


async def get_scenario_by_channel(pool: SQLitePool, channel_id: int) -> dict | None:
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM scenarios WHERE channel_id = $1", channel_id)
    return _scenario_row_to_dict(row)


async def bind_scenario_channel(
    pool: SQLitePool, guild_id: int, title: str, channel_id: int
) -> bool:
    async with pool.acquire() as conn:
        try:
            result = await conn.execute(
                "UPDATE scenarios SET channel_id = $1 WHERE guild_id = $2 AND title = $3",
                channel_id,
                guild_id,
                title,
            )
        except sqlite3.IntegrityError:
            return False
    return result == "UPDATE 1"


async def get_roster(pool: SQLitePool, scenario_id: int) -> list[dict]:
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


async def join_scenario(pool: SQLitePool, scenario_id: int, character_id: int) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO scenario_participants (scenario_id, character_id)
            SELECT $1, id FROM characters WHERE id = $2 AND role = 'PC'
            ON CONFLICT DO NOTHING
            """,
            scenario_id,
            character_id,
        )


async def advance_narration_position(
    pool: SQLitePool,
    scenario_id: int,
    expected_scene_index: int,
    expected_line_index: int,
    scene_index: int,
    line_index: int,
) -> bool:
    async with pool.acquire() as conn:
        result = await conn.execute(
            """UPDATE scenarios SET current_scene_index = $1, current_line_index = $2
            WHERE id = $3 AND current_scene_index = $4 AND current_line_index = $5""",
            scene_index,
            line_index,
            scenario_id,
            expected_scene_index,
            expected_line_index,
        )
    return result == "UPDATE 1"
