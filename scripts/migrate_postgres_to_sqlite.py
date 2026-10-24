"""Copy CoC-Bot tables from PostgreSQL into a new, empty SQLite database."""

import argparse
import asyncio
import json
import os
from datetime import date, datetime
from pathlib import Path
import sys

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import storage

TABLES = ("scenarios", "characters", "scenario_participants")
JSON_COLUMNS = {"skills", "structure"}


def _sqlite_value(column: str, value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if column in JSON_COLUMNS and value is not None and not isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return int(value)
    return value


async def migrate(postgres_url: str, sqlite_path: str) -> dict[str, int]:
    pool = await storage.create_pool(sqlite_path)
    postgres = await asyncpg.connect(postgres_url)
    try:
        async with pool.acquire() as target:
            counts = {
                table: await target.fetchval(f"SELECT COUNT(*) FROM {table}")
                for table in TABLES
            }
            if any(counts.values()):
                raise RuntimeError("대상 SQLite DB가 비어 있지 않습니다. 빈 파일을 지정해주세요.")

            async with target.transaction():
                async with postgres.transaction(isolation="repeatable_read", readonly=True):
                    for table in TABLES:
                        if table == "scenario_participants":
                            rows = await postgres.fetch(
                                "SELECT * FROM scenario_participants ORDER BY scenario_id, character_id"
                            )
                        else:
                            rows = await postgres.fetch(f"SELECT * FROM {table} ORDER BY id")
                        for row in rows:
                            columns = list(row.keys())
                            names = ", ".join(f'"{name}"' for name in columns)
                            placeholders = ", ".join("?" for _ in columns)
                            values = [_sqlite_value(name, row[name]) for name in columns]
                            await target.execute(
                                f"INSERT INTO {table} ({names}) VALUES ({placeholders})", *values
                            )
                        counts[table] = len(rows)
        return counts
    finally:
        await postgres.close()
        await pool.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sqlite-path",
        default=os.environ.get("DATABASE_PATH", "data/coc-bot.sqlite3"),
        help="새 SQLite 파일 경로 (기본값: DATABASE_PATH 또는 data/coc-bot.sqlite3)",
    )
    args = parser.parse_args()
    postgres_url = os.environ.get("POSTGRES_URL") or os.environ.get("DATABASE_URL")
    if not postgres_url:
        raise SystemExit("POSTGRES_URL 또는 기존 DATABASE_URL 환경변수를 설정해주세요.")
    counts = asyncio.run(migrate(postgres_url, args.sqlite_path))
    print("SQLite로 복사 완료: " + ", ".join(f"{name}={count}" for name, count in counts.items()))


if __name__ == "__main__":
    main()
