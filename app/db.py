"""SQLite connection and schema. No ORM (see spec Implementation Decisions)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from app import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'editor')),
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL CHECK (kind IN ('post', 'page')),
    title TEXT NOT NULL,
    slug TEXT NOT NULL,
    body_md TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK (status IN ('draft', 'published')) DEFAULT 'draft',
    author_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (kind, slug)
);

-- One row per saved version of a content item (see CONTEXT.md: Revision).
-- `version` counts 1, 2, 3... within one item; `rolled_back_to` is set when
-- the save was a Roll back, to the version it rolled back to.
CREATE TABLE IF NOT EXISTS revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id INTEGER NOT NULL REFERENCES content(id),
    version INTEGER NOT NULL,
    title TEXT NOT NULL,
    slug TEXT NOT NULL,
    body_md TEXT NOT NULL,
    saved_by INTEGER NOT NULL REFERENCES users(id),
    saved_at TEXT NOT NULL DEFAULT (datetime('now')),
    rolled_back_to INTEGER,
    UNIQUE (content_id, version)
);
"""


# Items saved before revisions existed get one starting revision from their
# current state, so their pre-T15 text can still be rolled back to. The last
# editor was never stored, so the Author stands in as who saved it. A no-op
# once every item has a revision.
BACKFILL_REVISIONS = """
INSERT INTO revisions (content_id, version, title, slug, body_md, saved_by, saved_at)
SELECT id, 1, title, slug, body_md, author_id, updated_at FROM content
WHERE id NOT IN (SELECT content_id FROM revisions);
"""

# Database files already brought up to date by this process.
_schema_ready: set[str] = set()


def _path(db_path: Path | None) -> Path:
    # Read lazily (settings.DATABASE_PATH) so tests can monkeypatch it per-test.
    return db_path if db_path is not None else settings.DATABASE_PATH


def _open(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a connection to the CMS database. The first open of each file in
    a process runs init_db, so a database made before a newer table existed
    works without a re-seed."""
    path = _path(db_path)
    if str(Path(path).resolve()) not in _schema_ready:
        init_db(path)
    return _open(path)


def init_db(db_path: Path | None = None) -> None:
    """Create any missing tables and backfill starting revisions. Safe to run
    on a new or an existing database, any number of times."""
    path = _path(db_path)
    conn = _open(path)
    try:
        conn.executescript(SCHEMA + BACKFILL_REVISIONS)
        conn.commit()
    finally:
        conn.close()
    _schema_ready.add(str(Path(path).resolve()))
