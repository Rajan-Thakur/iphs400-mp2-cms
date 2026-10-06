"""T03: Posts — create, edit, delete, Markdown preview (ticket #4)."""
from __future__ import annotations

from app import content as content_module
from app import db as db_module
from app.security import hash_password
from tests.conftest import extract_csrf


def _csrf_from(client, path="/admin/posts/new"):
    page = client.get(path)
    return extract_csrf(page.text)


def test_editor_can_create_a_post_as_draft(client_as):
    editor = client_as("editor")
    csrf = _csrf_from(editor)
    response = editor.post(
        "/admin/posts/new",
        data={"title": "My First Post", "slug": "my-first-post", "body_md": "Hello.",
              "csrf_token": csrf},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/posts?saved=created"

    posts = content_module.list_content("post")
    assert len(posts) == 1
    assert posts[0]["title"] == "My First Post"
    assert posts[0]["status"] == "draft"


def test_editor_can_edit_a_post_authored_by_another_editor(client_as):
    # Seed a second editor account directly (the client_as fixture only knows
    # about the one demo editor), so this genuinely exercises cross-author edit.
    conn = db_module.connect()
    try:
        conn.execute(
            "INSERT INTO users (email, password_hash, role, active) VALUES (?, ?, 'editor', 1)",
            ("other-editor@example.test", hash_password("whatever-pw")),
        )
        conn.commit()
        other_id = conn.execute(
            "SELECT id FROM users WHERE email = ?", ("other-editor@example.test",)
        ).fetchone()["id"]
    finally:
        conn.close()

    post_id = content_module.create_content("post", "Original", "original", "v1", other_id)

    editor = client_as("editor")
    edit_page = editor.get(f"/admin/posts/{post_id}/edit")
    assert edit_page.status_code == 200
    csrf = extract_csrf(edit_page.text)
    response = editor.post(
        f"/admin/posts/{post_id}/edit",
        data={"title": "Edited", "slug": "original", "body_md": "v2", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert response.status_code == 303
    updated = content_module.get_content(post_id, "post")
    assert updated["title"] == "Edited"
    assert updated["body_md"] == "v2"


def test_editor_can_delete_a_post(client_as):
    editor = client_as("editor")
    csrf = _csrf_from(editor)
    editor.post("/admin/posts/new",
                data={"title": "Temp", "slug": "temp", "body_md": "x", "csrf_token": csrf})
    post_id = content_module.list_content("post")[0]["id"]

    list_page = editor.get("/admin/posts")
    csrf2 = extract_csrf(list_page.text)
    response = editor.post(f"/admin/posts/{post_id}/delete",
                            data={"csrf_token": csrf2}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/posts?saved=deleted"
    assert content_module.get_content(post_id, "post") is None


def test_create_post_rejects_missing_csrf(client_as):
    editor = client_as("editor")
    response = editor.post("/admin/posts/new",
                            data={"title": "x", "slug": "x", "body_md": "x"})
    assert response.status_code == 422


def test_create_post_rejects_wrong_csrf(client_as):
    editor = client_as("editor")
    response = editor.post(
        "/admin/posts/new",
        data={"title": "x", "slug": "x", "body_md": "x", "csrf_token": "wrong"},
    )
    assert response.status_code == 403


def test_edit_post_rejects_wrong_csrf(client_as):
    editor = client_as("editor")
    csrf = _csrf_from(editor)
    editor.post("/admin/posts/new",
                data={"title": "x", "slug": "x", "body_md": "x", "csrf_token": csrf})
    post_id = content_module.list_content("post")[0]["id"]

    response = editor.post(
        f"/admin/posts/{post_id}/edit",
        data={"title": "y", "slug": "x", "body_md": "y", "csrf_token": "wrong"},
    )
    assert response.status_code == 403
    assert content_module.get_content(post_id, "post")["title"] == "x"


def test_delete_post_rejects_wrong_csrf(client_as):
    editor = client_as("editor")
    csrf = _csrf_from(editor)
    editor.post("/admin/posts/new",
                data={"title": "x", "slug": "x", "body_md": "x", "csrf_token": csrf})
    post_id = content_module.list_content("post")[0]["id"]

    response = editor.post(f"/admin/posts/{post_id}/delete", data={"csrf_token": "wrong"})
    assert response.status_code == 403
    assert content_module.get_content(post_id, "post") is not None


def test_delete_post_does_not_delete_a_page_sharing_the_same_id():
    # Regression: delete_content must filter by kind, not just id — otherwise
    # a Post-delete request could remove a Page that happens to share its id
    # once Pages (T05) exist.
    conn = db_module.connect()
    try:
        admin_id = conn.execute(
            "SELECT id FROM users WHERE email = 'admin@example.test'"
        ).fetchone()["id"]
    finally:
        conn.close()
    page_id = content_module.create_content("page", "About", "about", "x", admin_id)
    content_module.delete_content(page_id, "post")
    assert content_module.get_content(page_id, "page") is not None


def test_create_post_rejects_duplicate_slug(client_as):
    editor = client_as("editor")
    csrf = _csrf_from(editor)
    editor.post("/admin/posts/new",
                data={"title": "One", "slug": "dup", "body_md": "a", "csrf_token": csrf})

    csrf2 = _csrf_from(editor)
    response = editor.post(
        "/admin/posts/new",
        data={"title": "Two", "slug": "dup", "body_md": "b", "csrf_token": csrf2},
    )
    assert response.status_code == 200
    assert "already used" in response.text.lower()
    assert len(content_module.list_content("post")) == 1


def test_preview_sanitizes_script_and_event_handlers(client_as):
    editor = client_as("editor")
    response = editor.post(
        "/admin/posts/preview",
        data={"body_md": "<script>alert(1)</script><img src=x onerror=alert(1)>"},
    )
    assert response.status_code == 200
    assert "<script" not in response.text
    assert "onerror" not in response.text


def test_preview_renders_markdown(client_as):
    editor = client_as("editor")
    response = editor.post("/admin/posts/preview", data={"body_md": "# Hi\n\nThere."})
    assert response.status_code == 200
    assert "<h1>Hi</h1>" in response.text


def test_admin_pages_link_a_stylesheet_that_resolves_at_any_depth(client_as):
    # T10: a bare "style.css" on /admin/posts/new resolved to
    # /admin/posts/style.css (404), so nested admin screens had no CSS.
    editor = client_as("editor")
    expected = {"/admin": "style.css", "/admin/content": "../style.css",
                "/admin/posts/new": "../../style.css"}
    for path, href in expected.items():
        assert f'rel="stylesheet" href="{href}"' in editor.get(path).text, path
    assert editor.get("/style.css").status_code == 200


def test_anonymous_is_redirected_from_posts_list(client):
    response = client.get("/admin/posts", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_seed_demo_creates_an_example_post(tmp_path):
    from app.seed import seed_posts, seed_users

    db_path = tmp_path / "seed-test.db"
    seed_users(db_path, "admin-pw", "editor-pw")
    seed_posts(db_path)

    conn = db_module.connect(db_path)
    try:
        count = conn.execute(
            "SELECT COUNT(*) AS n FROM content WHERE kind = 'post'"
        ).fetchone()["n"]
    finally:
        conn.close()
    assert count >= 1
