"""Content (Posts and Pages) data access. No ORM (see spec Implementation
Decisions). Posts and Pages share this one table and these functions,
distinguished only by `kind` ('post' | 'page') — see CONTEXT.md.
"""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone

from app import db as db_module

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

STATUS_DRAFT = "draft"
STATUS_PUBLISHED = "published"

# Not a Status: a Scheduled item is a Draft with a publish_at set (see
# CONTEXT.md). The lists, filters and dashboard counts show it apart from
# other Drafts, using this one expression.
LISTED_SCHEDULED = "scheduled"
LISTED_AS_SQL = (
    f"CASE WHEN content.status = '{STATUS_DRAFT}' AND content.publish_at IS NOT NULL "
    f"THEN '{LISTED_SCHEDULED}' ELSE content.status END"
)

# How every stored time is written: UTC, as SQLite's datetime('now') gives it.
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

# A Page is exported to site/<slug>.html, so these slugs would overwrite a
# file the export itself writes. Maps kind -> {slug: what it would clobber}.
RESERVED_SLUGS = {"page": {"index": "the site's home page"}}


def reserved_slug_reason(kind: str, slug: str) -> str | None:
    """What `slug` is reserved for within `kind`, or None if it's free."""
    return RESERVED_SLUGS.get(kind, {}).get(slug)


def normalize_slug(raw: str) -> str:
    return raw.strip().lower()


def validate_slug(raw: str) -> str | None:
    """Normalize `raw` and return it if it's a valid slug, else None."""
    normalized = normalize_slug(raw)
    return normalized if SLUG_RE.match(normalized) else None


def to_timestamp(moment: datetime) -> str:
    """`moment` in the stored UTC format. A naive datetime is taken as UTC."""
    if moment.tzinfo is not None:
        moment = moment.astimezone(timezone.utc)
    return moment.strftime(TIMESTAMP_FORMAT)


def parse_publish_at(raw: str) -> str | None:
    """A date and time typed into the Schedule form (e.g. "2026-10-08T09:30"
    from <input type="datetime-local">), read as UTC and returned in the
    stored format, or None if it can't be read."""
    try:
        return to_timestamp(datetime.fromisoformat(raw.strip()))
    except ValueError:
        return None


def list_content(kind: str) -> list[sqlite3.Row]:
    conn = db_module.connect()
    try:
        return conn.execute(
            f"SELECT content.*, {LISTED_AS_SQL} AS listed_as, users.email AS author_email "
            "FROM content "
            "JOIN users ON users.id = content.author_id "
            "WHERE content.kind = ? ORDER BY content.created_at DESC",
            (kind,),
        ).fetchall()
    finally:
        conn.close()


def list_published(kind: str) -> list[sqlite3.Row]:
    conn = db_module.connect()
    try:
        return conn.execute(
            "SELECT * FROM content WHERE kind = ? AND status = ? ORDER BY created_at DESC",
            (kind, STATUS_PUBLISHED),
        ).fetchall()
    finally:
        conn.close()


def count_by_status() -> dict[str, int]:
    """Combined draft/scheduled/published counts across both kinds (Posts and
    Pages together) — the dashboard shows one total, not split by type. A
    Scheduled item counts only as scheduled, so the three sum to the total."""
    conn = db_module.connect()
    try:
        rows = conn.execute(
            f"SELECT {LISTED_AS_SQL} AS listed_as, COUNT(*) AS n FROM content GROUP BY listed_as"
        ).fetchall()
    finally:
        conn.close()
    counts = {STATUS_DRAFT: 0, LISTED_SCHEDULED: 0, STATUS_PUBLISHED: 0}
    for row in rows:
        counts[row["listed_as"]] = row["n"]
    return counts


def list_filtered(*, status: str | None = None, kind: str | None = None) -> list[sqlite3.Row]:
    """All content (Posts and Pages together), optionally narrowed by
    status ('draft', 'scheduled' or 'published', as listed) and/or kind.
    None means "no filter" (show all) for that axis."""
    query = (
        f"SELECT content.*, {LISTED_AS_SQL} AS listed_as, users.email AS author_email "
        "FROM content JOIN users ON users.id = content.author_id WHERE 1 = 1"
    )
    params: list[str] = []
    if status is not None:
        query += f" AND {LISTED_AS_SQL} = ?"
        params.append(status)
    if kind is not None:
        query += " AND content.kind = ?"
        params.append(kind)
    query += " ORDER BY content.created_at DESC"

    conn = db_module.connect()
    try:
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def get_published_by_slug(kind: str, slug: str) -> sqlite3.Row | None:
    conn = db_module.connect()
    try:
        return conn.execute(
            "SELECT * FROM content WHERE kind = ? AND slug = ? AND status = ?",
            (kind, slug, STATUS_PUBLISHED),
        ).fetchone()
    finally:
        conn.close()


def get_content(content_id: int, kind: str) -> sqlite3.Row | None:
    conn = db_module.connect()
    try:
        return conn.execute(
            "SELECT * FROM content WHERE id = ? AND kind = ?", (content_id, kind)
        ).fetchone()
    finally:
        conn.close()


def _record_revision(conn: sqlite3.Connection, content_id: int, title: str, slug: str,
                     body_md: str, saved_by: int, rolled_back_to: int | None = None) -> None:
    """Record one save as the item's next Revision, inside the caller's
    transaction so the content row and its revision commit together."""
    conn.execute(
        "INSERT INTO revisions "
        "(content_id, version, title, slug, body_md, saved_by, rolled_back_to) "
        "SELECT ?, COALESCE(MAX(version), 0) + 1, ?, ?, ?, ?, ? "
        "FROM revisions WHERE content_id = ?",
        (content_id, title, slug, body_md, saved_by, rolled_back_to, content_id),
    )


def create_content(kind: str, title: str, slug: str, body_md: str, author_id: int) -> int:
    conn = db_module.connect()
    try:
        cur = conn.execute(
            "INSERT INTO content (kind, title, slug, body_md, author_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (kind, title, slug, body_md, author_id),
        )
        _record_revision(conn, cur.lastrowid, title, slug, body_md, author_id)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def update_content(content_id: int, kind: str, title: str, slug: str, body_md: str,
                   *, saved_by: int, rolled_back_to: int | None = None) -> None:
    """Save new values for an item and record them as its next revision.
    `saved_by` is the user saving (Admin or Editor); `rolled_back_to` is the
    version this save rolls back to, when it is a Roll back."""
    conn = db_module.connect()
    try:
        cur = conn.execute(
            "UPDATE content SET title = ?, slug = ?, body_md = ?, "
            "updated_at = datetime('now') WHERE id = ? AND kind = ?",
            (title, slug, body_md, content_id, kind),
        )
        if cur.rowcount:
            _record_revision(conn, content_id, title, slug, body_md, saved_by, rolled_back_to)
        conn.commit()
    finally:
        conn.close()


def get_revision(content_id: int, kind: str, version: int) -> sqlite3.Row | None:
    """One version of one item, or None. Looked up by the item's own id and
    kind, so a version number can never pull in another item's text."""
    conn = db_module.connect()
    try:
        return conn.execute(
            "SELECT revisions.* FROM revisions "
            "JOIN content ON content.id = revisions.content_id "
            "WHERE revisions.content_id = ? AND content.kind = ? AND revisions.version = ?",
            (content_id, kind, version),
        ).fetchone()
    finally:
        conn.close()


def list_revisions(content_id: int, kind: str) -> list[sqlite3.Row]:
    """An item's revisions, newest first, with who saved each one."""
    conn = db_module.connect()
    try:
        return conn.execute(
            "SELECT revisions.*, users.email AS saved_by_email FROM revisions "
            "JOIN content ON content.id = revisions.content_id "
            "JOIN users ON users.id = revisions.saved_by "
            "WHERE revisions.content_id = ? AND content.kind = ? "
            "ORDER BY revisions.version DESC",
            (content_id, kind),
        ).fetchall()
    finally:
        conn.close()


def set_status(content_id: int, kind: str, status: str) -> None:
    """Publish or unpublish by hand. Either way any schedule is cancelled:
    a Published item no longer needs it, and an unpublished one shouldn't
    come back on its own."""
    conn = db_module.connect()
    try:
        conn.execute(
            "UPDATE content SET status = ?, publish_at = NULL, updated_at = datetime('now') "
            "WHERE id = ? AND kind = ?",
            (status, content_id, kind),
        )
        conn.commit()
    finally:
        conn.close()


def set_schedule(content_id: int, kind: str, publish_at: str | None) -> bool:
    """Schedule a Draft for `publish_at` (stored UTC format), or cancel its
    schedule with None. Only a Draft can be scheduled; returns whether the
    item was one. Records no Revision: like Publish, it changes Status, not
    content."""
    conn = db_module.connect()
    try:
        cur = conn.execute(
            "UPDATE content SET publish_at = ? WHERE id = ? AND kind = ? AND status = ?",
            (publish_at, content_id, kind, STATUS_DRAFT),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def publish_due(now: datetime | None = None) -> list[sqlite3.Row]:
    """Publish every Scheduled item whose time has come (publish_at <= now,
    UTC; default the current time) and return them. `cms publish` calls this
    before writing site/, so a Scheduled item becomes Published on the first
    export after its time."""
    now_stamp = to_timestamp(now or datetime.now(timezone.utc))
    conn = db_module.connect()
    try:
        now_published = conn.execute(
            "UPDATE content SET status = ?, publish_at = NULL, updated_at = datetime('now') "
            "WHERE status = ? AND publish_at IS NOT NULL AND publish_at <= ? "
            "RETURNING kind, title, slug",
            (STATUS_PUBLISHED, STATUS_DRAFT, now_stamp),
        ).fetchall()
        conn.commit()
        return now_published
    finally:
        conn.close()


def delete_content(content_id: int, kind: str) -> None:
    conn = db_module.connect()
    try:
        cur = conn.execute("DELETE FROM content WHERE id = ? AND kind = ?", (content_id, kind))
        if cur.rowcount:
            conn.execute("DELETE FROM revisions WHERE content_id = ?", (content_id,))
        conn.commit()
    finally:
        conn.close()
