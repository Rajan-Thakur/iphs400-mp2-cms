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


def _seed_content(
    db_path: Path, *, kind: str, title: str, slug: str, body_md: str,
    status: str, author_email: str,
) -> None:
    conn = db_module.connect(db_path)
    try:
        author = conn.execute(
            "SELECT id FROM users WHERE email = ?", (author_email,)
        ).fetchone()
        conn.execute(
            "INSERT OR IGNORE INTO content (kind, title, slug, body_md, status, author_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (kind, title, slug, body_md, status, author["id"]),
        )
        conn.commit()
    finally:
        conn.close()


def seed_posts(db_path: Path) -> None:
    """Seed one published and one draft Post, authored by the demo editor, so
    a fresh clone has a feed to look at — and a draft that must never leave
    the database."""
    _seed_content(
        db_path, kind="post", title="Welcome", slug="welcome",
        body_md=(
            "This site is managed with a small, WordPress-style CMS: "
            "Editors draft Posts and Pages in a local admin console, and an Admin "
            "publishes them to this static site.\n\n"
            "- Posts appear in the feed on the home page.\n"
            "- Pages appear in the navigation.\n"
        ),
        status="published", author_email=DEMO_EMAILS["editor"],
    )
    _seed_content(
        db_path, kind="post", title="Upcoming changes (draft)", slug="upcoming-changes",
        body_md="Still being written — drafts stay in the admin console until published.",
        status="draft", author_email=DEMO_EMAILS["editor"],
    )


def seed_pages(db_path: Path) -> None:
    """Seed one example Page, published so the public site's nav shows
    something immediately after a fresh seed."""
    _seed_content(
        db_path, kind="page", title="About", slug="about",
        body_md="# About\n\nThis is an example page seeded for demo purposes.",
        status="published", author_email=DEMO_EMAILS["admin"],
    )
