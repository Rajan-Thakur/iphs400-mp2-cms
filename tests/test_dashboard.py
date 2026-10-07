"""T08: admin console dashboard and filters (ticket #9)."""
from __future__ import annotations

import re

from app import content as content_module
from app import db as db_module


def _author_id() -> int:
    conn = db_module.connect()
    try:
        return conn.execute(
            "SELECT id FROM users WHERE email = 'admin@example.test'"
        ).fetchone()["id"]
    finally:
        conn.close()


def _visible_text(html: str) -> str:
    """The page as a reader sees it: tags dropped, whitespace collapsed."""
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def _seed(kind: str, slug: str, status: str) -> int:
    author_id = _author_id()
    content_id = content_module.create_content(kind, slug.title(), slug, "Body.", author_id)
    if status == "published":
        content_module.set_status(content_id, kind, "published")
    return content_id


def test_dashboard_shows_a_combined_count_across_posts_and_pages(client_as):
    _seed("post", "draft-post", "draft")
    _seed("post", "published-post", "published")
    _seed("page", "draft-page", "draft")
    _seed("page", "published-page-1", "published")
    _seed("page", "published-page-2", "published")

    response = client_as("editor").get("/admin")
    assert response.status_code == 200
    assert "2 drafts" in _visible_text(response.text)
    assert "3 published" in _visible_text(response.text)


def test_dashboard_count_matches_the_database_exactly(client_as):
    assert content_module.count_by_status() == {"draft": 0, "scheduled": 0, "published": 0}
    response = client_as("editor").get("/admin")
    assert "0 drafts" in _visible_text(response.text)
    assert "0 published" in _visible_text(response.text)


def test_content_list_filters_by_status_alone(client_as):
    _seed("post", "a-draft", "draft")
    _seed("page", "a-published", "published")

    editor = client_as("editor")
    response = editor.get("/admin/content?status=draft")
    assert "A-draft".lower() in response.text.lower()
    assert "a-published" not in response.text.lower()


def test_content_list_filters_by_type_alone(client_as):
    _seed("post", "some-post", "draft")
    _seed("page", "some-page", "draft")

    editor = client_as("editor")
    response = editor.get("/admin/content?type=page")
    assert "some-page" in response.text.lower()
    assert "some-post" not in response.text.lower()


def test_content_list_filters_by_status_and_type_together(client_as):
    _seed("post", "draft-post-x", "draft")
    _seed("post", "published-post-x", "published")
    _seed("page", "draft-page-x", "draft")
    _seed("page", "published-page-x", "published")

    editor = client_as("editor")
    response = editor.get("/admin/content?status=published&type=post")
    text = response.text.lower()
    assert "published-post-x" in text
    assert "draft-post-x" not in text
    assert "draft-page-x" not in text
    assert "published-page-x" not in text


def test_content_list_with_no_filters_shows_everything(client_as):
    _seed("post", "post-one", "draft")
    _seed("page", "page-one", "published")

    editor = client_as("editor")
    response = editor.get("/admin/content")
    text = response.text.lower()
    assert "post-one" in text
    assert "page-one" in text


def test_content_list_ignores_an_invalid_status_value(client_as):
    _seed("post", "post-one", "draft")

    editor = client_as("editor")
    response = editor.get("/admin/content?status=bogus")
    assert response.status_code == 200
    assert "post-one" in response.text.lower()


def test_content_list_ignores_an_invalid_type_value(client_as):
    _seed("post", "post-one", "draft")

    editor = client_as("editor")
    response = editor.get("/admin/content?type=bogus")
    assert response.status_code == 200
    assert "post-one" in response.text.lower()


def test_anonymous_is_redirected_from_content_overview(client):
    response = client.get("/admin/content", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
