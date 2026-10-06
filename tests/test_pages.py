"""T05: Pages — CRUD plus public navigation (ticket #6)."""
from __future__ import annotations

from app import content as content_module
from app import publish as publish_module
from app.main import create_app
from fastapi.testclient import TestClient
from tests.conftest import extract_csrf


def _csrf_from(client, path="/admin/pages/new"):
    return extract_csrf(client.get(path).text)


def test_editor_can_create_a_page_as_draft(client_as):
    editor = client_as("editor")
    csrf = _csrf_from(editor)
    response = editor.post(
        "/admin/pages/new",
        data={"title": "About", "slug": "about", "body_md": "Hello.", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/pages?saved=created"
    pages = content_module.list_content("page")
    assert len(pages) == 1
    assert pages[0]["status"] == "draft"


def test_editor_can_edit_and_delete_a_page(client_as):
    editor = client_as("editor")
    csrf = _csrf_from(editor)
    editor.post("/admin/pages/new",
                data={"title": "About", "slug": "about", "body_md": "v1", "csrf_token": csrf})
    page_id = content_module.list_content("page")[0]["id"]

    edit_page = editor.get(f"/admin/pages/{page_id}/edit")
    assert edit_page.status_code == 200
    csrf2 = extract_csrf(edit_page.text)
    response = editor.post(
        f"/admin/pages/{page_id}/edit",
        data={"title": "About Us", "slug": "about", "body_md": "v2", "csrf_token": csrf2},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert content_module.get_content(page_id, "page")["title"] == "About Us"

    csrf3 = extract_csrf(editor.get("/admin/pages").text)
    response = editor.post(f"/admin/pages/{page_id}/delete",
                            data={"csrf_token": csrf3}, follow_redirects=False)
    assert response.status_code == 303
    assert content_module.get_content(page_id, "page") is None


def test_admin_can_publish_and_unpublish_a_page(client_as):
    editor = client_as("editor")
    csrf = _csrf_from(editor)
    editor.post("/admin/pages/new",
                data={"title": "About", "slug": "about", "body_md": "x", "csrf_token": csrf})
    page_id = content_module.list_content("page")[0]["id"]

    admin = client_as("admin")
    csrf2 = extract_csrf(admin.get("/admin/pages").text)
    response = admin.post(f"/admin/pages/{page_id}/publish",
                           data={"csrf_token": csrf2}, follow_redirects=False)
    assert response.status_code == 303
    assert content_module.get_content(page_id, "page")["status"] == "published"

    csrf3 = extract_csrf(admin.get("/admin/pages").text)
    response = admin.post(f"/admin/pages/{page_id}/unpublish",
                           data={"csrf_token": csrf3}, follow_redirects=False)
    assert response.status_code == 303
    assert content_module.get_content(page_id, "page")["status"] == "draft"


def test_editor_cannot_publish_a_page(client_as):
    editor = client_as("editor")
    csrf = _csrf_from(editor)
    editor.post("/admin/pages/new",
                data={"title": "About", "slug": "about", "body_md": "x", "csrf_token": csrf})
    page_id = content_module.list_content("page")[0]["id"]

    csrf2 = extract_csrf(editor.get("/admin/pages").text)
    response = editor.post(f"/admin/pages/{page_id}/publish", data={"csrf_token": csrf2})
    assert response.status_code == 403
    assert "Only an Admin can publish" in response.text


def test_page_crud_rejects_wrong_csrf(client_as):
    editor = client_as("editor")
    response = editor.post(
        "/admin/pages/new",
        data={"title": "About", "slug": "about", "body_md": "x", "csrf_token": "wrong"},
    )
    assert response.status_code == 403
    assert content_module.list_content("page") == []


def test_page_slug_reserved_by_the_export_is_rejected(client_as):
    # T10: a Page is exported to site/<slug>.html, so slug "index" would
    # overwrite the home page.
    editor = client_as("editor")
    response = editor.post(
        "/admin/pages/new",
        data={"title": "Home?", "slug": "Index", "body_md": "x", "csrf_token": _csrf_from(editor)},
    )
    assert response.status_code == 200
    assert "reserved" in response.text.lower()
    assert content_module.list_content("page") == []


def test_editing_a_page_to_a_reserved_slug_is_rejected(client_as):
    editor = client_as("editor")
    editor.post("/admin/pages/new",
                data={"title": "About", "slug": "about", "body_md": "x", "csrf_token": _csrf_from(editor)})
    page_id = content_module.list_content("page")[0]["id"]

    csrf = extract_csrf(editor.get(f"/admin/pages/{page_id}/edit").text)
    response = editor.post(f"/admin/pages/{page_id}/edit",
                           data={"title": "About", "slug": "index", "body_md": "x", "csrf_token": csrf})
    assert response.status_code == 200
    assert "reserved" in response.text.lower()
    assert content_module.get_content(page_id, "page")["slug"] == "about"


def test_post_slug_index_is_still_allowed(client_as):
    # Posts export under posts/, so "index" collides with nothing there.
    editor = client_as("editor")
    response = editor.post(
        "/admin/posts/new",
        data={"title": "Index", "slug": "index", "body_md": "x",
              "csrf_token": extract_csrf(editor.get("/admin/posts/new").text)},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_page_preview_sanitizes_script(client_as):
    editor = client_as("editor")
    response = editor.post(
        "/admin/pages/preview",
        data={"body_md": "<script>alert(1)</script>Safe text"},
    )
    assert response.status_code == 200
    assert "<script" not in response.text
    assert "Safe text" in response.text


def test_anonymous_is_redirected_from_pages_list(client):
    response = client.get("/admin/pages", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_published_page_appears_in_public_nav_draft_does_not(client_as):
    editor = client_as("editor")
    csrf = _csrf_from(editor)
    editor.post("/admin/pages/new", data={
        "title": "Published Page", "slug": "published-page",
        "body_md": "x", "csrf_token": csrf,
    })
    csrf2 = _csrf_from(editor)
    editor.post("/admin/pages/new", data={
        "title": "Draft Page", "slug": "draft-page",
        "body_md": "x", "csrf_token": csrf2,
    })
    published_id = next(
        p["id"] for p in content_module.list_content("page") if p["slug"] == "published-page"
    )

    admin = client_as("admin")
    csrf3 = extract_csrf(admin.get("/admin/pages").text)
    admin.post(f"/admin/pages/{published_id}/publish", data={"csrf_token": csrf3})

    items = publish_module.nav_items()
    titles = [item["title"] for item in items]
    assert "Published Page" in titles
    assert "Draft Page" not in titles

    nav_item = next(item for item in items if item["title"] == "Published Page")
    assert nav_item["href"] == "published-page.html"
    assert not nav_item["href"].startswith("/")


def test_public_home_route_shows_nav_for_published_pages(client_as):
    editor = client_as("editor")
    csrf = _csrf_from(editor)
    editor.post("/admin/pages/new", data={
        "title": "Nav Page", "slug": "nav-page", "body_md": "x", "csrf_token": csrf,
    })
    page_id = content_module.list_content("page")[0]["id"]
    admin = client_as("admin")
    csrf2 = extract_csrf(admin.get("/admin/pages").text)
    admin.post(f"/admin/pages/{page_id}/publish", data={"csrf_token": csrf2})

    anon = TestClient(create_app())
    response = anon.get("/")
    assert response.status_code == 200
    assert "Nav Page" in response.text
    assert 'href="nav-page.html"' in response.text


def test_render_site_nav_lists_published_pages_only(tmp_path):
    # Seed two pages directly via the data layer (no HTTP round-trip needed
    # for this one — it's exercising render_site(), not the routes).
    from app import db as db_module
    admin_id = db_module.connect().execute(
        "SELECT id FROM users WHERE email = 'admin@example.test'"
    ).fetchone()["id"]
    published_id = content_module.create_content(
        "page", "Live Page", "live-page", "x", admin_id,
    )
    content_module.set_status(published_id, "page", "published")
    content_module.create_content("page", "Draft Page", "draft-only", "x", admin_id)

    out = publish_module.render_site(tmp_path / "site")
    html = (out / "index.html").read_text()
    assert "Live Page" in html
    assert "Draft Page" not in html
    assert 'href="/' not in html


def test_seed_demo_creates_an_example_page(tmp_path):
    from app import db as db_module
    from app.seed import seed_pages, seed_users

    db_path = tmp_path / "seed-test.db"
    seed_users(db_path, "admin-pw", "editor-pw")
    seed_pages(db_path)

    conn = db_module.connect(db_path)
    try:
        row = conn.execute(
            "SELECT status FROM content WHERE kind = 'page'"
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row["status"] == "published"
