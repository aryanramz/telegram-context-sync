from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from typing import Iterator, Sequence


SCHEMA = """
CREATE TABLE IF NOT EXISTS chats (
    name TEXT PRIMARY KEY,
    identifier TEXT NOT NULL,
    export_file TEXT,
    last_message_id INTEGER DEFAULT 0,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_name TEXT NOT NULL,
    chat_identifier TEXT NOT NULL,
    message_id INTEGER NOT NULL,
    message_date TEXT NOT NULL,
    sender_id TEXT,
    sender_name TEXT,
    text TEXT NOT NULL,
    synced_at TEXT NOT NULL,
    UNIQUE(chat_name, message_id)
);

CREATE INDEX IF NOT EXISTS idx_messages_chat_date
ON messages(chat_name, message_date);

CREATE INDEX IF NOT EXISTS idx_messages_chat_message_id
ON messages(chat_name, message_id);
"""


@contextmanager
def connect(db_path: Path) -> Iterator[sqlite3.Connection]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Path) -> None:
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)


def upsert_chat(
    conn: sqlite3.Connection,
    *,
    name: str,
    identifier: str,
    export_file: str | None,
    updated_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO chats(name, identifier, export_file, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            identifier = excluded.identifier,
            export_file = excluded.export_file,
            updated_at = excluded.updated_at
        """,
        (name, identifier, export_file, updated_at),
    )


def get_last_message_id(conn: sqlite3.Connection, chat_name: str) -> int:
    row = conn.execute(
        "SELECT last_message_id FROM chats WHERE name = ?",
        (chat_name,),
    ).fetchone()
    return int(row["last_message_id"]) if row and row["last_message_id"] is not None else 0


def insert_messages(conn: sqlite3.Connection, rows: Sequence[dict]) -> int:
    if not rows:
        return 0

    before = conn.total_changes
    conn.executemany(
        """
        INSERT OR IGNORE INTO messages(
            chat_name,
            chat_identifier,
            message_id,
            message_date,
            sender_id,
            sender_name,
            text,
            synced_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["chat_name"],
                row["chat_identifier"],
                row["message_id"],
                row["message_date"],
                row.get("sender_id"),
                row.get("sender_name"),
                row["text"],
                row["synced_at"],
            )
            for row in rows
        ],
    )
    return conn.total_changes - before


def update_last_message_id(conn: sqlite3.Connection, chat_name: str, last_message_id: int, updated_at: str) -> None:
    conn.execute(
        """
        UPDATE chats
        SET last_message_id = MAX(COALESCE(last_message_id, 0), ?),
            updated_at = ?
        WHERE name = ?
        """,
        (last_message_id, updated_at, chat_name),
    )


def list_chats(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(conn.execute("SELECT * FROM chats ORDER BY name"))


def fetch_recent_messages(conn: sqlite3.Connection, chat_name: str, limit: int) -> list[sqlite3.Row]:
    rows = conn.execute(
        """
        SELECT *
        FROM messages
        WHERE chat_name = ?
        ORDER BY message_date DESC, message_id DESC
        LIMIT ?
        """,
        (chat_name, limit),
    ).fetchall()
    return list(reversed(rows))
