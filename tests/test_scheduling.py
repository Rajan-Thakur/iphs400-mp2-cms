"""T16: Scheduled publishing (ticket #18). Every time is UTC. Tests that
cross the "is it due yet?" line pass a fixed `now`; route and CLI tests use
times far in the past (2000) or future (2999), so none depends on the clock."""
from __future__ import annotations

import sqlite3
from datetime import datetime

from app import cli
from app import content as content_module
from app import db as db_module
from app import settings
from tests.conftest import extract_csrf
from tests.test_dashboard import _visible_text

PAST = "2000-01-01T09:00"
FUTURE = "2999-01-01T09:00"


def _admin_id() -> int:
    conn = db_module.connect()
    try:
        return conn.execute(
            "SELECT id FROM users WHERE email = 'admin@example.test'").fetchone()["id"]
    finally:
        conn.close()


def _draft(kind="post", slug="later", title="Later") -> int:
    return content_module.create_content(kind, title, slug, "body", _admin_id())


def _schedule(client, item_id, publish_at, kind="post"):
    csrf = extract_csrf(client.get(f"/admin/{kind}s/{item_id}/edit").text)
    return client.post(f"/admin/{kind}s/{item_id}/schedule",
                       data={"publish_at": publish_at, "csrf_token": csrf},
                       follow_redirects=False)


# -- reading the form's time --

def test_a_datetime_local_value_is_read_as_utc():
    assert content_module.parse_publish_at("2026-10-08T09:30") == "2026-10-08 09:30:00"
    assert content_module.parse_publish_at(" 2026-10-08T09:30:15 ") == "2026-10-08 09:30:15"


def test_an_unreadable_time_is_none():
    assert content_module.parse_publish_at("") is None
    assert content_module.parse_publish_at("next tuesday") is None
    assert content_module.parse_publish_at("2026-13-40T99:00") is None


# -- what becomes Published, and when --

def test_publish_due_publishes_only_scheduled_drafts_whose_time_has_come():
    due = _draft(slug="due")
    exactly_now = _draft(slug="exactly-now")
    future = _draft(slug="future")
    plain = _draft(slug="plain")
    content_module.set_schedule(due, "post", "2026-10-08 08:00:00")
    content_module.set_schedule(exactly_now, "post", "2026-10-08 09:00:00")
    content_module.set_schedule(future, "post", "2026-10-08 09:00:01")

    now_published = content_module.publish_due(datetime(2026, 10, 8, 9, 0, 0))

    assert sorted(item["slug"] for item in now_published) == ["due", "exactly-now"]
    for item_id, status in [(due, "published"), (exactly_now, "published"),
                            (future, "draft"), (plain, "draft")]:
        assert content_module.get_content(item_id, "post")["status"] == status
    # Once Published, the schedule is spent.
    assert content_module.get_content(due, "post")["publish_at"] is None
    assert content_module.get_content(future, "post")["publish_at"] == "2026-10-08 09:00:01"


def test_cms_publish_switches_due_items_to_published_and_exports_only_them(
        monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(settings, "SITE", tmp_path / "site")
    due = _draft(slug="due-post", title="Due Post")
    later = _draft(slug="later-post", title="Later Post")
    content_module.set_schedule(due, "post", "2000-01-01 09:00:00")
    content_module.set_schedule(later, "post", "2999-01-01 09:00:00")

    assert cli.main(["publish"]) == 0

    assert (tmp_path / "site" / "posts" / "due-post.html").exists()
    assert not (tmp_path / "site" / "posts" / "later-post.html").exists()
    assert "Later Post" not in (tmp_path / "site" / "index.html").read_text(encoding="utf-8")
    assert content_module.get_content(due, "post")["status"] == "published"
    assert content_module.get_content(later, "post")["status"] == "draft"
    assert "Due Post" in capsys.readouterr().out


# -- the admin screens --

def test_admin_schedules_a_draft_and_the_edit_screen_says_when_in_utc(client_as):
    admin = client_as("admin")
    post_id = _draft()

    response = _schedule(admin, post_id, FUTURE)

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/posts?saved=scheduled"
    assert content_module.get_content(post_id, "post")["publish_at"] == "2999-01-01 09:00:00"
    assert "Post scheduled." in admin.get(response.headers["location"]).text
    edit = admin.get(f"/admin/posts/{post_id}/edit").text
    assert "2999-01-01 09:00 UTC" in edit
    assert "next <code>cms publish</code>" in edit
    assert "Cancel schedule" in edit


def test_admin_cancels_a_schedule(client_as):
    admin = client_as("admin")
    post_id = _draft()
    content_module.set_schedule(post_id, "post", "2999-01-01 09:00:00")

    csrf = extract_csrf(admin.get(f"/admin/posts/{post_id}/edit").text)
    response = admin.post(f"/admin/posts/{post_id}/cancel-schedule", data={"csrf_token": csrf},
                          follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/posts?saved=schedule-cancelled"
    assert content_module.get_content(post_id, "post")["publish_at"] is None
    assert content_module.get_content(post_id, "post")["status"] == "draft"
    assert "Schedule cancelled." in admin.get(response.headers["location"]).text


def test_a_past_or_unreadable_time_is_refused_and_changes_nothing(client_as):
    admin = client_as("admin")
    post_id = _draft()
    content_module.set_schedule(post_id, "post", "2999-01-01 09:00:00")

    for bad, message in [(PAST, "must be in the future"), ("soon", "Enter a date and time")]:
        response = _schedule(admin, post_id, bad)
        assert response.status_code == 200, bad
        assert message in response.text, bad
        assert content_module.get_content(post_id, "post")["publish_at"] == "2999-01-01 09:00:00"


def test_a_published_item_cannot_be_scheduled(client_as):
    admin = client_as("admin")
    post_id = _draft()
    content_module.set_status(post_id, "post", content_module.STATUS_PUBLISHED)

    response = _schedule(admin, post_id, FUTURE)

    assert response.status_code == 200
    assert "Only a draft can be scheduled" in response.text
    assert content_module.get_content(post_id, "post")["publish_at"] is None

    csrf = extract_csrf(admin.get(f"/admin/posts/{post_id}/edit").text)
    response = admin.post(f"/admin/posts/{post_id}/cancel-schedule", data={"csrf_token": csrf},
                          follow_redirects=False)
    assert response.status_code == 200
    assert "already published" in response.text


def test_editors_see_no_schedule_controls(client_as):
    post_id = _draft()
    assert f'{post_id}/schedule"' not in client_as("editor").get(
        f"/admin/posts/{post_id}/edit").text
    assert f'{post_id}/schedule"' in client_as("admin").get(
        f"/admin/posts/{post_id}/edit").text


def test_publishing_by_hand_clears_the_schedule(client_as):
    admin = client_as("admin")
    post_id = _draft()
    content_module.set_schedule(post_id, "post", "2999-01-01 09:00:00")

    csrf = extract_csrf(admin.get("/admin/posts").text)
    admin.post(f"/admin/posts/{post_id}/publish", data={"csrf_token": csrf})
    assert content_module.get_content(post_id, "post")["publish_at"] is None

    # Unpublished again, it's a plain Draft: nothing brings it back on its own.
    csrf = extract_csrf(admin.get("/admin/posts").text)
    admin.post(f"/admin/posts/{post_id}/unpublish", data={"csrf_token": csrf})
    assert content_module.get_content(post_id, "post")["publish_at"] is None
    assert content_module.publish_due(datetime(3000, 1, 1)) == []


def test_scheduling_records_no_revision(client_as):
    admin = client_as("admin")
    post_id = _draft()

    _schedule(admin, post_id, FUTURE)
    csrf = extract_csrf(admin.get(f"/admin/posts/{post_id}/edit").text)
    admin.post(f"/admin/posts/{post_id}/cancel-schedule", data={"csrf_token": csrf})

    assert len(content_module.list_revisions(post_id, "post")) == 1


def test_pages_can_be_scheduled_too(client_as):
    admin = client_as("admin")
    page_id = _draft(kind="page", slug="soon")

    response = _schedule(admin, page_id, FUTURE, kind="page")

    assert response.headers["location"] == "/admin/pages?saved=scheduled"
    assert content_module.get_content(page_id, "page")["publish_at"] == "2999-01-01 09:00:00"


# -- lists and dashboard --

def test_lists_and_dashboard_show_scheduled_apart_from_drafts(client_as):
    admin = client_as("admin")
    scheduled = _draft(slug="scheduled-one", title="Scheduled One")
    _draft(slug="plain-draft", title="Plain Draft")
    published = _draft(slug="published-one", title="Published One")
    scheduled_page = _draft(kind="page", slug="scheduled-page", title="Scheduled Page")
    content_module.set_schedule(scheduled, "post", "2999-01-01 09:00:00")
    content_module.set_schedule(scheduled_page, "page", "2999-01-01 10:00:00")
    content_module.set_status(published, "post", content_module.STATUS_PUBLISHED)

    assert content_module.count_by_status() == {"draft": 1, "scheduled": 2, "published": 1}
    assert sorted(i["slug"] for i in content_module.list_filtered(status="scheduled")) == [
        "scheduled-one", "scheduled-page"]
    assert [i["slug"] for i in content_module.list_filtered(status="draft")] == ["plain-draft"]

    badge = 'badge--scheduled">scheduled</span>'
    posts = admin.get("/admin/posts").text
    assert badge in posts and "2999-01-01 09:00 UTC" in posts
    pages = admin.get("/admin/pages").text
    assert badge in pages and "2999-01-01 10:00 UTC" in pages
    overview = admin.get("/admin/content?status=scheduled").text
    assert overview.count(badge) == 2
    assert "Scheduled One" in overview and "Plain Draft" not in overview
    dashboard = admin.get("/admin").text
    for count in ("1 drafts", "2 scheduled", "1 published"):
        assert count in _visible_text(dashboard), count
    assert "admin/content?status=scheduled" in dashboard


# -- existing databases --

# The schema exactly as it was before this ticket: no publish_at column.
PRE_T16_SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'editor')),
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE content (
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
CREATE TABLE revisions (
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
INSERT INTO users (email, password_hash, role) VALUES ('old@example.test', 'x', 'admin');
INSERT INTO content (kind, title, slug, body_md, author_id)
    VALUES ('post', 'Old Post', 'old-post', 'written before T16', 1);
"""


def test_a_database_from_before_scheduling_gains_publish_at(monkeypatch, tmp_path):
    old_db = tmp_path / "pre-t16.db"
    conn = sqlite3.connect(old_db)
    conn.executescript(PRE_T16_SCHEMA)
    conn.close()
    monkeypatch.setattr(settings, "DATABASE_PATH", old_db)

    assert content_module.get_content(1, "post")["publish_at"] is None
    content_module.set_schedule(1, "post", "2999-01-01 09:00:00")
    assert content_module.get_content(1, "post")["publish_at"] == "2999-01-01 09:00:00"
    assert content_module.get_content(1, "post")["title"] == "Old Post"
