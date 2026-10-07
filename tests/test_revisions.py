"""T15: Revision history with rollback (ticket #16)."""
from __future__ import annotations

import re
import sqlite3

from app import content as content_module
from app import settings
from app.seed import seed_posts
from tests.conftest import extract_csrf

TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC")


def _create_post(client, title="First", slug="first", body_md="v1") -> int:
    csrf = extract_csrf(client.get("/admin/posts/new").text)
    client.post("/admin/posts/new",
                data={"title": title, "slug": slug, "body_md": body_md, "csrf_token": csrf})
    # By slug, not list order: two posts made in the same second tie on created_at.
    return next(post["id"] for post in content_module.list_content("post")
                if post["slug"] == slug)


def _edit_post(client, post_id, *, title, slug, body_md):
    csrf = extract_csrf(client.get(f"/admin/posts/{post_id}/edit").text)
    return client.post(f"/admin/posts/{post_id}/edit",
                       data={"title": title, "slug": slug, "body_md": body_md,
                             "csrf_token": csrf},
                       follow_redirects=False)


def _revision_rows(html: str) -> list[str]:
    """The text of each row in the edit screen's revision list, in page order."""
    return [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", row)).strip()
            for row in re.findall(r'<li class="revision">(.*?)</li>', html, re.S)]


def test_each_save_is_listed_as_a_revision_newest_first(client_as):
    editor = client_as("editor")
    post_id = _create_post(editor, title="First", slug="first", body_md="v1")
    _edit_post(editor, post_id, title="Second", slug="first", body_md="v2")

    rows = _revision_rows(editor.get(f"/admin/posts/{post_id}/edit").text)

    assert len(rows) == 2
    assert "Version 2" in rows[0] and "Second" in rows[0] and "Current" in rows[0]
    assert "Version 1" in rows[1] and "First" in rows[1] and "Current" not in rows[1]
    assert "editor@example.test" in rows[0] and TIMESTAMP.search(rows[0])
    # Each version's Markdown can be read; only earlier versions offer Roll back.
    assert "v2" in rows[0] and "v1" in rows[1]
    assert "Roll back" not in rows[0] and "Roll back" in rows[1]


def _roll_back(client, post_id, version):
    csrf = extract_csrf(client.get(f"/admin/posts/{post_id}/edit").text)
    return client.post(f"/admin/posts/{post_id}/revisions/{version}/rollback",
                       data={"csrf_token": csrf}, follow_redirects=False)


def test_rolling_back_returns_to_an_earlier_version_as_a_new_revision(client_as):
    editor = client_as("editor")
    post_id = _create_post(editor, title="First", slug="first", body_md="v1")
    _edit_post(editor, post_id, title="Second", slug="second", body_md="v2")

    response = _roll_back(client_as("admin"), post_id, 1)

    assert response.status_code == 303
    post = content_module.get_content(post_id, "post")
    assert (post["title"], post["slug"], post["body_md"]) == ("First", "first", "v1")
    rows = _revision_rows(editor.get(f"/admin/posts/{post_id}/edit").text)
    assert len(rows) == 3
    assert "Version 3" in rows[0] and "Current" in rows[0]
    assert "Rolled back to version 1" in rows[0] and "admin@example.test" in rows[0]


def test_rolling_back_to_a_slug_now_taken_shows_the_error_and_changes_nothing(client_as):
    editor = client_as("editor")
    post_id = _create_post(editor, title="First", slug="first", body_md="v1")
    _edit_post(editor, post_id, title="Second", slug="second", body_md="v2")
    _create_post(editor, title="Newcomer", slug="first", body_md="mine now")

    response = _roll_back(editor, post_id, 1)

    assert response.status_code == 200
    assert "That slug is already used by another post." in response.text
    post = content_module.get_content(post_id, "post")
    assert (post["title"], post["slug"], post["body_md"]) == ("Second", "second", "v2")
    assert len(_revision_rows(editor.get(f"/admin/posts/{post_id}/edit").text)) == 2


def test_a_version_of_a_different_item_cannot_be_rolled_back_to(client_as):
    editor = client_as("editor")
    other_id = _create_post(editor, title="Other", slug="other", body_md="other v1")
    _edit_post(editor, other_id, title="Other v2", slug="other", body_md="other v2")
    post_id = _create_post(editor, title="Mine", slug="mine", body_md="mine v1")

    # Version 2 exists only on the other post; a Page id isn't a Post at all.
    _roll_back(editor, post_id, 2)
    page_csrf = extract_csrf(editor.get("/admin/pages/new").text)
    editor.post("/admin/pages/new", data={"title": "A Page", "slug": "a-page",
                                          "body_md": "page", "csrf_token": page_csrf})
    page_id = content_module.list_content("page")[0]["id"]
    csrf = extract_csrf(editor.get(f"/admin/pages/{page_id}/edit").text)
    editor.post(f"/admin/posts/{page_id}/revisions/1/rollback", data={"csrf_token": csrf})

    post = content_module.get_content(post_id, "post")
    assert (post["title"], post["body_md"]) == ("Mine", "mine v1")
    page = content_module.get_content(page_id, "page")
    assert (page["title"], page["body_md"]) == ("A Page", "page")
    assert len(_revision_rows(editor.get(f"/admin/posts/{post_id}/edit").text)) == 1


def test_pages_keep_revisions_and_roll_back_too(client_as):
    admin = client_as("admin")
    csrf = extract_csrf(admin.get("/admin/pages/new").text)
    admin.post("/admin/pages/new", data={"title": "About", "slug": "about",
                                         "body_md": "old", "csrf_token": csrf})
    page_id = content_module.list_content("page")[0]["id"]
    csrf = extract_csrf(admin.get(f"/admin/pages/{page_id}/edit").text)
    admin.post(f"/admin/pages/{page_id}/edit", data={"title": "About us", "slug": "about",
                                                      "body_md": "new", "csrf_token": csrf})

    csrf = extract_csrf(admin.get(f"/admin/pages/{page_id}/edit").text)
    response = admin.post(f"/admin/pages/{page_id}/revisions/1/rollback",
                          data={"csrf_token": csrf}, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/pages?saved=rolled-back"
    page = content_module.get_content(page_id, "page")
    assert (page["title"], page["body_md"]) == ("About", "old")
    assert "Page rolled back." in admin.get(response.headers["location"]).text


# The schema exactly as it was before this ticket: no revisions table.
PRE_T15_SCHEMA = """
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
INSERT INTO users (email, password_hash, role) VALUES ('old@example.test', 'x', 'admin');
INSERT INTO content (kind, title, slug, body_md, author_id, updated_at)
    VALUES ('post', 'Old Post', 'old-post', 'written before T15', 1, '2026-10-01 12:00:00');
"""


def test_a_database_from_before_revisions_gets_a_starting_revision(monkeypatch, tmp_path):
    old_db = tmp_path / "pre-t15.db"
    conn = sqlite3.connect(old_db)
    conn.executescript(PRE_T15_SCHEMA)
    conn.close()
    monkeypatch.setattr(settings, "DATABASE_PATH", old_db)

    revisions = content_module.list_revisions(1, "post")

    assert [(r["version"], r["title"], r["body_md"], r["saved_by_email"], r["saved_at"])
            for r in revisions] == [
        (1, "Old Post", "written before T15", "old@example.test", "2026-10-01 12:00:00")]


def test_seeded_demo_content_starts_with_a_first_revision():
    seed_posts(settings.DATABASE_PATH)

    welcome = next(post for post in content_module.list_content("post")
                   if post["slug"] == "welcome")
    revisions = content_module.list_revisions(welcome["id"], "post")
    assert [(r["version"], r["title"]) for r in revisions] == [(1, "Welcome")]
