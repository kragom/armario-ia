"""
Almacenamiento de usuarios y sesiones en SQLite
"""
import hashlib
import secrets
import aiosqlite
from typing import Optional

from storage.db import DB_PATH


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{h}"


def _verify_password(password: str, stored: str) -> bool:
    salt, h = stored.split(":", 1)
    return h == hashlib.sha256((salt + password).encode()).hexdigest()


async def init_auth_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                password_hash TEXT DEFAULT '',
                has_set_password INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)
        """)

        # Migración: añadir columnas si no existen
        for col in ["zodiac_sign", "weather_location"]:
            try:
                await db.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT DEFAULT ''")
            except Exception:
                pass

        await db.commit()

        cursor = await db.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        if row[0] == 0:
            await db.execute("INSERT OR IGNORE INTO users (username, display_name) VALUES (?, ?)", ("naomi", "Naomi"))
            await db.execute("INSERT OR IGNORE INTO users (username, display_name) VALUES (?, ?)", ("hector", "Héctor"))
            await db.commit()
            await db.execute("UPDATE users SET username = 'naomi', display_name = 'Naomi' WHERE username = 'noemi'")
            await db.commit()


async def get_user(username: str) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)


async def get_user_by_id(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)


async def set_user_password(username: str, password: str) -> bool:
    h = _hash_password(password)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET password_hash = ?, has_set_password = 1 WHERE username = ?", (h, username))
        await db.commit()
    return True


async def verify_login(username: str, password: str) -> Optional[dict]:
    user = await get_user(username)
    if user is None:
        return {"error": "User not found"}
    if not user["has_set_password"]:
        return user
    if _verify_password(password, user["password_hash"]):
        return user
    return {"error": "Invalid password"}


async def change_password(user_id: int, current_password: str, new_password: str) -> bool:
    user = await get_user_by_id(user_id)
    if user is None:
        return False
    if user["has_set_password"] and not _verify_password(current_password, user["password_hash"]):
        return False
    h = _hash_password(new_password)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET password_hash = ?, has_set_password = 1 WHERE id = ?", (h, user_id))
        await db.commit()
    return True


async def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO sessions (user_id, token) VALUES (?, ?)", (user_id, token))
        await db.commit()
    return token


async def get_session_user(token: str) -> Optional[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return row["user_id"]


async def delete_session(token: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM sessions WHERE token = ?", (token,))
        await db.commit()


async def update_user_profile(user_id: int, zodiac_sign: str = "", weather_location: str = "") -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE users SET zodiac_sign = ?, weather_location = ? WHERE id = ?",
            (zodiac_sign, weather_location, user_id)
        )
        await db.commit()
        return cursor.rowcount > 0