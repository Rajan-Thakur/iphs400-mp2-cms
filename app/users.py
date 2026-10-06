"""User account data access: create, change role, deactivate. No ORM
(see spec Implementation Decisions)."""
from __future__ import annotations

import re
import sqlite3

from app import db as db_module
from app.security import hash_password

ROLES = {"admin", "editor"}

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email(raw: str) -> str | None:
    """Normalize `raw` and return it if it looks like an email, else None."""
    normalized = raw.strip().lower()
    return normalized if EMAIL_RE.match(normalized) else None


def list_users() -> list[sqlite3.Row]:
    conn = db_module.connect()
    try:
        return conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    finally:
        conn.close()


def get_user(user_id: int) -> sqlite3.Row | None:
    conn = db_module.connect()
    try:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    finally:
        conn.close()


def create_user(email: str, password: str, role: str) -> int:
    conn = db_module.connect()
    try:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, role, active) VALUES (?, ?, ?, 1)",
            (email, hash_password(password), role),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def set_role(user_id: int, role: str) -> None:
    conn = db_module.connect()
    try:
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        conn.commit()
    finally:
        conn.close()


def deactivate_user(user_id: int) -> None:
    conn = db_module.connect()
    try:
        conn.execute("UPDATE users SET active = 0 WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()
