"""T10: the dev server serves the public site at the same paths the static
export writes, published content only (ticket #11)."""
from __future__ import annotations

from app import content as content_module
from app import db as db_module


def _seed(kind: str, title: str, slug: str, status: str) -> None:
    conn = db_module.connect()
    try:
        author_id = conn.execute(
            "SELECT id FROM users WHERE email = 'admin@example.test'"
        ).fetchone()["id"]
    finally:
        conn.close()
    content_id = content_module.create_content(kind, title, slug, f"# {title}", author_id)
    if status == "published":
        content_module.set_status(content_id, kind, "published")


def test_home_lists_published_posts_but_not_drafts(client):
    _seed("post", "Live Post", "live-post", "published")
    _seed("post", "Hidden Draft", "hidden-draft", "draft")

    for path in ("/", "/index.html"):
        html = client.get(path).text
        assert 'href="posts/live-post.html"' in html
        assert "Hidden Draft" not in html


def test_published_post_is_served_and_a_draft_is_404(client):
    _seed("post", "Live Post", "live-post", "published")
    _seed("post", "Hidden Draft", "hidden-draft", "draft")

    response = client.get("/posts/live-post.html")
    assert response.status_code == 200
    assert "<h1>Live Post</h1>" in response.text
    assert client.get("/posts/hidden-draft.html").status_code == 404


def test_published_page_is_served_and_a_draft_is_404(client):
    _seed("page", "About", "about", "published")
    _seed("page", "Secret", "secret", "draft")

    response = client.get("/about.html")
    assert response.status_code == 200
    assert "<h1>About</h1>" in response.text
    assert client.get("/secret.html").status_code == 404


def test_nav_link_from_a_post_page_resolves_on_the_dev_server(client):
    _seed("post", "Live Post", "live-post", "published")
    _seed("page", "About", "about", "published")

    html = client.get("/posts/live-post.html").text
    assert 'href="../about.html"' in html  # /posts/../about.html -> /about.html
    assert client.get("/about.html").status_code == 200
    assert client.get("/style.css").status_code == 200
