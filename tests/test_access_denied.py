"""An Editor who reaches an admin-only page or action gets a real "access
denied" page in the admin layout, not raw JSON (ticket #14). Still a 403;
anonymous visitors are still sent to login.
"""
from __future__ import annotations

import pytest

from app import content as content_module
from tests.conftest import DEMO_USERS, extract_csrf, log_in
from tests.test_admin_links import assert_links_resolve
from tests.test_phone_width import assert_fits_phone


@pytest.mark.parametrize("path", ["/admin/users", "/admin/users/new"])
def test_editor_on_a_user_management_page_sees_an_access_denied_page(client_as, path):
    response = client_as("editor").get(path)

    assert response.status_code == 403
    assert response.headers["content-type"].startswith("text/html")
    assert "Only an Admin can manage users" in response.text
    assert DEMO_USERS["editor"]["email"] in response.text  # the admin nav is still there


def test_editor_publishing_sees_the_publish_reason_on_the_page(client_as):
    editor = client_as("editor")
    editor.post("/admin/posts/new", data={
        "title": "T", "slug": "t", "body_md": "x",
        "csrf_token": extract_csrf(editor.get("/admin/posts/new").text)})
    post_id = content_module.list_content("post")[0]["id"]
    csrf = extract_csrf(editor.get("/admin/posts").text)

    response = editor.post(f"/admin/posts/{post_id}/publish", data={"csrf_token": csrf})

    assert response.status_code == 403
    assert response.headers["content-type"].startswith("text/html")
    assert "Only an Admin can publish" in response.text
    # Rendered at /admin/posts/<id>/publish, a level deeper than a GET page.
    assert_links_resolve(editor, f"/admin/posts/{post_id}/publish", response.text)


def test_access_denied_page_links_back_and_every_link_resolves(client_as):
    editor = client_as("editor")
    response = editor.get("/admin/users/new")
    assert 'href="../../admin"' in response.text  # back to the dashboard, relatively
    assert_links_resolve(editor, "/admin/users/new", response.text)


def test_anonymous_visitor_is_still_redirected_to_login(client):
    response = client.get("/admin/users", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].endswith("/login")


def test_not_found_is_unchanged(client):
    response = client.get("/posts/no-such-post.html")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_access_denied_page_fits_a_phone(phone):
    log_in(phone, "editor")
    phone.goto("/admin/users")
    assert phone.inner_text("h1") == "Access denied"
    assert_fits_phone(phone)
