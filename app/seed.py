"""Demo user and content creation, shared by scripts/seed_demo.py and the
test fixtures."""
from __future__ import annotations

from pathlib import Path

from app import db as db_module
from app.security import hash_password

DEMO_EMAILS = {"admin": "admin@example.test", "editor": "editor@example.test"}


def seed_users(db_path: Path, admin_password: str, editor_password: str) -> None:
    db_module.init_db(db_path)
    conn = db_module.connect(db_path)
    try:
        conn.execute(
            "INSERT OR IGNORE INTO users (email, password_hash, role, active) "
            "VALUES (?, ?, 'admin', 1)",
            (DEMO_EMAILS["admin"], hash_password(admin_password)),
        )
        conn.execute(
            "INSERT OR IGNORE INTO users (email, password_hash, role, active) "
            "VALUES (?, ?, 'editor', 1)",
            (DEMO_EMAILS["editor"], hash_password(editor_password)),
        )
        conn.commit()
    finally:
        conn.close()


def seed_posts(db_path: Path) -> None:
    """Seed one example Post, authored by the demo editor, so a fresh clone
    has something to look at without hand-creating content first."""
    conn = db_module.connect(db_path)
    try:
        author = conn.execute(
            "SELECT id FROM users WHERE email = ?", (DEMO_EMAILS["editor"],)
        ).fetchone()
        conn.execute(
            "INSERT OR IGNORE INTO content (kind, title, slug, body_md, status, author_id) "
            "VALUES ('post', ?, ?, ?, 'draft', ?)",
            ("Welcome", "welcome",
             "# Welcome\n\nThis is an example post seeded for demo purposes.",
             author["id"]),
        )
        conn.commit()
    finally:
        conn.close()
