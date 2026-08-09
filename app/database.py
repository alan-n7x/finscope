from datetime import UTC, datetime
from pathlib import Path

import aiosqlite


def sqlite_path(database_url: str) -> str:
    prefix = "sqlite+aiosqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("DATABASE_URL deve usar sqlite+aiosqlite:///")
    path = database_url.removeprefix(prefix)
    if not path:
        raise ValueError("DATABASE_URL não contém um arquivo")
    return path


async def initialize_database(database_url: str) -> None:
    path = sqlite_path(database_url)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS connected_items (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                pluggy_item_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        await db.commit()


async def save_item(database_url: str, item_id: str) -> None:
    now = datetime.now(UTC).isoformat()
    async with aiosqlite.connect(sqlite_path(database_url)) as db:
        await db.execute(
            """
            INSERT INTO connected_items (id, pluggy_item_id, created_at, updated_at)
            VALUES (1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                pluggy_item_id = excluded.pluggy_item_id,
                updated_at = excluded.updated_at
            """,
            (item_id, now, now),
        )
        await db.commit()
