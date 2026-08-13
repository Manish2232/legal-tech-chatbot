"""SQLite persistence layer for LexAssist users and conversations."""

from __future__ import annotations

import datetime
import hashlib
import os
import secrets
import smtplib
import sqlite3
from contextlib import contextmanager
from email.message import EmailMessage
from pathlib import Path
from uuid import uuid4


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


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt.hex() + ":" + hashed.hex()


def _verify_password(password: str, stored_hash: str) -> bool:
    salt_hex, hash_hex = stored_hash.split(":", 1)
    salt = bytes.fromhex(salt_hex)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return derived.hex() == hash_hex


def _send_verification_email(email: str, code: str) -> bool:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender_email = os.getenv("SMTP_FROM_EMAIL", smtp_user or "noreply@lexassist.local")

    if not smtp_host or not smtp_user or not smtp_password:
        print(f"WARNING: SMTP not configured. Email verification code for {email}: {code}")
        return False

    try:
        message = EmailMessage()
        message["Subject"] = "LexAssist email verification"
        message["From"] = sender_email
        message["To"] = email
        message.set_content(
            "Your LexAssist verification code is: "
            f"{code}\n\nUse it to complete your sign-up in the app."
        )

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(message)
        return True
    except Exception as e:
        print(f"ERROR: Failed to send verification email to {email}: {e}")
        print(f"Fallback verification code for {email}: {code}")
        return False


def initialize_database() -> None:
    """Create the local database and migrate older schemas to the current version."""
    with _connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                email_verified INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS email_verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                code TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS password_resets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                code TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );

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
            """
        )

        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(conversations)").fetchall()
        }
        if "user_id" not in columns:
            connection.execute(
                "ALTER TABLE conversations ADD COLUMN user_id TEXT NOT NULL DEFAULT 'guest-user'"
            )

        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id, id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id, updated_at DESC)"
        )


def _conversation_title(message: str) -> str:
    """Use the first question as a readable label in the chat archive."""
    normalized = " ".join(message.split())
    return f"{normalized[:57].rstrip()}..." if len(normalized) > 60 else normalized


def register_user(name: str, email: str, password: str) -> dict[str, str | bool | None]:
    """Create a new account and issue a verification code."""
    name = (name or "").strip()
    email = (email or "").strip().lower()
    password = (password or "").strip()

    if not name or not email or not password:
        raise ValueError("Name, email, and password are required.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")

    initialize_database()
    with _connection() as connection:
        existing = connection.execute(
            "SELECT user_id FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if existing:
            raise ValueError("An account with that email already exists.")

        user_id = str(uuid4())
        password_hash = _hash_password(password)
        connection.execute(
            "INSERT INTO users (user_id, name, email, password_hash) VALUES (?, ?, ?, ?)",
            (user_id, name, email, password_hash),
        )

        code = f"{secrets.randbelow(900000) + 100000:06d}"
        expires_at = datetime.datetime.utcnow().timestamp() + (15 * 60)
        connection.execute(
            "INSERT INTO email_verifications (user_id, code, expires_at) VALUES (?, ?, ?)",
            (user_id, code, str(expires_at)),
        )

    email_sent = _send_verification_email(email, code)
    return {
        "user_id": user_id,
        "name": name,
        "email": email,
        "email_verified": False,
        "verification_code": code if not email_sent else None,
        "email_sent": email_sent,
    }


def get_user_by_email(email: str) -> dict[str, str | int | bool] | None:
    """Fetch a user by email address."""
    initialize_database()
    with _connection() as connection:
        row = connection.execute(
            "SELECT user_id, name, email, password_hash, email_verified, created_at FROM users WHERE email = ?",
            (email.lower().strip(),),
        ).fetchone()
    if not row:
        return None
    return {
        "user_id": row["user_id"],
        "name": row["name"],
        "email": row["email"],
        "password_hash": row["password_hash"],
        "email_verified": bool(row["email_verified"]),
        "created_at": row["created_at"],
    }


def authenticate_user(email: str, password: str) -> dict[str, str | int | bool] | None:
    """Authenticate the user only if credentials are valid and the email is verified."""
    user = get_user_by_email(email)
    if not user:
        return None
    if not _verify_password(password, str(user["password_hash"])):
        return None
    if not user["email_verified"]:
        raise ValueError("Please verify your email before logging in.")
    return user


def verify_email(email: str, code: str) -> dict[str, str | int | bool] | None:
    """Verify the user email using the code sent to them."""
    user = get_user_by_email(email)
    if not user:
        raise ValueError("Account not found.")

    initialize_database()
    with _connection() as connection:
        verification = connection.execute(
            "SELECT code, expires_at FROM email_verifications WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user["user_id"],),
        ).fetchone()
        if not verification:
            raise ValueError("No verification code was created for this account.")
        if verification["code"] != code.strip():
            raise ValueError("The verification code is incorrect.")

        expires_at = float(verification["expires_at"])
        if expires_at < datetime.datetime.utcnow().timestamp():
            raise ValueError("The verification code has expired. Please request a new one.")

        connection.execute(
            "UPDATE users SET email_verified = 1 WHERE user_id = ?",
            (user["user_id"],),
        )
        connection.execute(
            "DELETE FROM email_verifications WHERE user_id = ?",
            (user["user_id"],),
        )

    return get_user_by_email(email)


def resend_verification_code(email: str) -> dict[str, bool | str | None]:
    """Create a fresh verification code for an existing unverified user."""
    user = get_user_by_email(email)
    if not user:
        raise ValueError("Account not found.")

    initialize_database()
    with _connection() as connection:
        connection.execute(
            "DELETE FROM email_verifications WHERE user_id = ?",
            (user["user_id"],),
        )
        code = f"{secrets.randbelow(900000) + 100000:06d}"
        expires_at = datetime.datetime.utcnow().timestamp() + (15 * 60)
        connection.execute(
            "INSERT INTO email_verifications (user_id, code, expires_at) VALUES (?, ?, ?)",
            (user["user_id"], code, str(expires_at)),
        )

    email_sent = _send_verification_email(str(user["email"]), code)
    return {
        "email": str(user["email"]),
        "email_sent": email_sent,
        "verification_code": code if not email_sent else None,
    }


def request_password_reset(email: str) -> dict[str, bool | str | None]:
    """Send a reset code for a registered user's account."""
    user = get_user_by_email(email)
    if not user:
        raise ValueError("No account was found for that email address.")

    initialize_database()
    with _connection() as connection:
        connection.execute(
            "DELETE FROM password_resets WHERE user_id = ?",
            (user["user_id"],),
        )
        code = f"{secrets.randbelow(900000) + 100000:06d}"
        expires_at = datetime.datetime.utcnow().timestamp() + (15 * 60)
        connection.execute(
            "INSERT INTO password_resets (user_id, code, expires_at) VALUES (?, ?, ?)",
            (user["user_id"], code, str(expires_at)),
        )

    email_sent = _send_reset_email(str(user["email"]), code)
    return {
        "email": str(user["email"]),
        "email_sent": email_sent,
        "reset_code": code if not email_sent else None,
    }


def _send_reset_email(email: str, code: str) -> bool:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender_email = os.getenv("SMTP_FROM_EMAIL", smtp_user or "noreply@lexassist.local")

    if not smtp_host or not smtp_user or not smtp_password:
        print(f"WARNING: SMTP not configured. Email reset code for {email}: {code}")
        return False

    try:
        message = EmailMessage()
        message["Subject"] = "LexAssist password reset"
        message["From"] = sender_email
        message["To"] = email
        message.set_content(
            "Your LexAssist password reset code is: "
            f"{code}\n\nUse it to set a new password in the app."
        )

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(message)
        return True
    except Exception as e:
        print(f"ERROR: Failed to send reset email to {email}: {e}")
        print(f"Fallback reset code for {email}: {code}")
        return False


def reset_password(email: str, code: str, new_password: str) -> None:
    """Verify the reset code and update the account password."""
    user = get_user_by_email(email)
    if not user:
        raise ValueError("No account was found for that email address.")
    if len(new_password or "") < 8:
        raise ValueError("New password must be at least 8 characters long.")

    initialize_database()
    with _connection() as connection:
        reset_record = connection.execute(
            "SELECT code, expires_at FROM password_resets WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user["user_id"],),
        ).fetchone()
        if not reset_record:
            raise ValueError("No password reset request was found for this account.")
        if reset_record["code"] != code.strip():
            raise ValueError("The reset code is incorrect.")

        expires_at = float(reset_record["expires_at"])
        if expires_at < datetime.datetime.utcnow().timestamp():
            raise ValueError("The reset code has expired. Please request a new one.")

        new_hash = _hash_password(new_password)
        connection.execute(
            "UPDATE users SET password_hash = ? WHERE user_id = ?",
            (new_hash, user["user_id"]),
        )
        connection.execute(
            "DELETE FROM password_resets WHERE user_id = ?",
            (user["user_id"],),
        )


def save_message(session_id: str, role: str, content: str, user_id: str | None = None) -> None:
    """Store a chat message and associate it with the logged-in user."""
    if role not in {"user", "assistant"}:
        raise ValueError("Message role must be 'user' or 'assistant'.")

    initialize_database()
    user_id = user_id or "guest-user"
    with _connection() as connection:
        conversation_exists = connection.execute(
            "SELECT 1 FROM conversations WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if not conversation_exists:
            title = _conversation_title(content) if role == "user" else "New conversation"
            connection.execute(
                "INSERT INTO conversations (session_id, user_id, title) VALUES (?, ?, ?)",
                (session_id, user_id, title),
            )
        else:
            connection.execute(
                "UPDATE conversations SET user_id = ? WHERE session_id = ?",
                (user_id, session_id),
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


def delete_conversation(session_id: str) -> None:
    """Permanently delete one conversation and all of its saved messages."""
    initialize_database()
    with _connection() as connection:
        connection.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))


def list_conversations(user_id: str | None = None) -> list[dict[str, str]]:
    """Return saved chats for a specific user, newest first, for the sidebar archive."""
    initialize_database()
    with _connection() as connection:
        if user_id:
            rows = connection.execute(
                """
                SELECT session_id, title, updated_at
                FROM conversations
                WHERE user_id = ?
                ORDER BY updated_at DESC, rowid DESC
                """,
                (user_id,),
            ).fetchall()
        else:
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
