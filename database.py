"""SQLite persistence layer for LexAssist conversations."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path


DATABASE_PATH = Path(__file__).with_name("lexassist.db")


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def _connection() -> sqlite3.Connection:
    """Commit each operation and always release the SQLite file lock."""
    connection = _connect()
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize_database() -> None:
    """Create the local database and tables when the app first starts."""
    with _connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                session_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES conversations(session_id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_session_id
                ON messages(session_id, id);
            """
        )


def _conversation_title(message: str) -> str:
    """Use the first question as a readable label in the chat archive."""
    normalized = " ".join(message.split())
    return f"{normalized[:57].rstrip()}..." if len(normalized) > 60 else normalized


def save_message(session_id: str, role: str, content: str) -> None:
    """Store one message and create its conversation on first use."""
    if role not in {"user", "assistant"}:
        raise ValueError("Message role must be 'user' or 'assistant'.")

    initialize_database()
    with _connection() as connection:
        conversation_exists = connection.execute(
            "SELECT 1 FROM conversations WHERE session_id = ?", (session_id,)
        ).fetchone()
        if not conversation_exists:
            title = _conversation_title(content) if role == "user" else "New conversation"
            connection.execute(
                "INSERT INTO conversations (session_id, title) VALUES (?, ?)",
                (session_id, title),
            )

        connection.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        connection.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
            (session_id,),
        )


def get_messages(session_id: str) -> list[dict[str, str | int]]:
    """Return messages in the order they were sent."""
    initialize_database()
    with _connection() as connection:
        rows = connection.execute(
            "SELECT id, role, content FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
    return [
        {"id": row["id"], "role": row["role"], "content": row["content"]}
        for row in rows
    ]


def update_assistant_message(session_id: str, message_id: int, content: str) -> None:
    """Update one saved LexAssist response after a user edits it."""
    content = content.strip()
    if not content:
        raise ValueError("An answer cannot be empty.")

    initialize_database()
    with _connection() as connection:
        result = connection.execute(
            """
            UPDATE messages
            SET content = ?
            WHERE id = ? AND session_id = ? AND role = 'assistant'
            """,
            (content, message_id, session_id),
        )
        if result.rowcount != 1:
            raise ValueError("The saved answer could not be found.")
        connection.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
            (session_id,),
        )


def list_conversations() -> list[dict[str, str]]:
    """Return saved chats, newest first, for the sidebar archive."""
    initialize_database()
    with _connection() as connection:
        rows = connection.execute(
            """
            SELECT session_id, title, updated_at
            FROM conversations
            ORDER BY updated_at DESC, rowid DESC
            """
        ).fetchall()
    return [
        {
            "session_id": row["session_id"],
            "title": row["title"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


if __name__ == "__main__":
    initialize_database()
    print(f"LexAssist database is ready: {DATABASE_PATH}")
