"""T04: publish and unpublish for Posts (ticket #5)."""
from __future__ import annotations

from app import content as content_module
from app.main import create_app
from fastapi.testclient import TestClient
from tests.conftest import extract_csrf


def _create_draft(client_as, slug="draft-post"):
    editor = client_as("editor")
    page = editor.get("/admin/posts/new")
    csrf = extract_csrf(page.text)
    editor.post("/admin/posts/new",
                data={"title": "Draft", "slug": slug, "body_md": "x", "csrf_token": csrf})
    return content_module.list_content("post")[0]["id"]


def test_admin_can_publish_a_draft_post(client_as):
    post_id = _create_draft(client_as)

    admin = client_as("admin")
    list_page = admin.get("/admin/posts")
    csrf = extract_csrf(list_page.text)
    response = admin.post(f"/admin/posts/{post_id}/publish",
                           data={"csrf_token": csrf}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/posts?saved=published"
    assert content_module.get_content(post_id, "post")["status"] == "published"


def test_admin_can_unpublish_a_published_post(client_as):
    post_id = _create_draft(client_as, slug="to-unpublish")
    admin = client_as("admin")
    csrf = extract_csrf(admin.get("/admin/posts").text)
    admin.post(f"/admin/posts/{post_id}/publish", data={"csrf_token": csrf})

    csrf2 = extract_csrf(admin.get("/admin/posts").text)
    response = admin.post(f"/admin/posts/{post_id}/unpublish",
                           data={"csrf_token": csrf2}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/posts?saved=unpublished"
    assert content_module.get_content(post_id, "post")["status"] == "draft"


def test_editor_cannot_publish_and_gets_a_specific_reason(client_as):
    post_id = _create_draft(client_as, slug="editor-cannot-publish")
    editor = client_as("editor")
    csrf = extract_csrf(editor.get("/admin/posts").text)
    response = editor.post(f"/admin/posts/{post_id}/publish", data={"csrf_token": csrf})
    assert response.status_code == 403
    assert "Only an Admin can publish" in response.text
    assert content_module.get_content(post_id, "post")["status"] == "draft"


def test_editor_cannot_unpublish_and_gets_a_specific_reason(client_as):
    post_id = _create_draft(client_as, slug="editor-cannot-unpublish")
    admin = client_as("admin")
    admin.post(f"/admin/posts/{post_id}/publish",
               data={"csrf_token": extract_csrf(admin.get("/admin/posts").text)})

    editor = client_as("editor")
    csrf = extract_csrf(editor.get("/admin/posts").text)
    response = editor.post(f"/admin/posts/{post_id}/unpublish", data={"csrf_token": csrf})
    assert response.status_code == 403
    assert "Only an Admin can publish" in response.text
    assert content_module.get_content(post_id, "post")["status"] == "published"


def test_admin_retains_full_editor_crud_on_posts(client_as):
    admin = client_as("admin")
    csrf = extract_csrf(admin.get("/admin/posts/new").text)
    response = admin.post("/admin/posts/new",
                           data={"title": "Admin Post", "slug": "admin-post",
                                 "body_md": "x", "csrf_token": csrf},
                           follow_redirects=False)
    assert response.status_code == 303
    post_id = content_module.list_content("post")[0]["id"]

    edit_page = admin.get(f"/admin/posts/{post_id}/edit")
    csrf2 = extract_csrf(edit_page.text)
    response = admin.post(f"/admin/posts/{post_id}/edit",
                           data={"title": "Admin Post Edited", "slug": "admin-post",
                                 "body_md": "y", "csrf_token": csrf2},
                           follow_redirects=False)
    assert response.status_code == 303
    assert content_module.get_content(post_id, "post")["title"] == "Admin Post Edited"

    csrf3 = extract_csrf(admin.get("/admin/posts").text)
    response = admin.post(f"/admin/posts/{post_id}/delete",
                           data={"csrf_token": csrf3}, follow_redirects=False)
    assert response.status_code == 303
    assert content_module.get_content(post_id, "post") is None


def test_publish_status_persists_across_a_server_restart(client_as):
    post_id = _create_draft(client_as, slug="persists")
    admin = client_as("admin")
    admin.post(f"/admin/posts/{post_id}/publish",
               data={"csrf_token": extract_csrf(admin.get("/admin/posts").text)})

    # A brand-new app instance, with its own fresh connections, against the
    # same on-disk db file stands in for a server restart: nothing is held
    # in memory between requests or across app instances. Read the status
    # back through THIS instance's own routes, not a side-channel query, so
    # the test actually proves the restarted server's own code sees it.
    fresh_app_client = TestClient(create_app())
    login_page = fresh_app_client.get("/login")
    csrf = extract_csrf(login_page.text)
    fresh_app_client.post("/login", data={
        "email": "admin@example.test", "password": "test-admin-pw", "csrf_token": csrf,
    })
    posts_page = fresh_app_client.get("/admin/posts")
    assert posts_page.status_code == 200
    # The restarted app's own template only renders "Unpublish" when it reads
    # status == "published" back from the db — this is the proof the status
    # survived, not a side-channel SQL query that would pass even if the
    # route/template layer never saw the change.
    assert "Unpublish" in posts_page.text
    assert f"/admin/posts/{post_id}/unpublish" in posts_page.text
