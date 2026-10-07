"""T09: security and access-control completeness sweep (ticket #10).

No new feature. Exhaustively re-verifies, across every admin route in the
app -- not just the one or two routes each earlier ticket happened to test
as a side effect of its own functional tests:

  1. An anonymous visitor is redirected to /login (never served the page).
  2. Where a route is admin-only (not editor-accessible), an Editor gets 403.
  3. Every state-changing (POST) admin form rejects a forged CSRF token.

Route lists use "{post_id}"/"{page_id}" placeholders, filled in from real
rows the `seeded_ids` fixture creates, because some routes (content_crud's
update_item) check the item exists before checking CSRF -- a fake id would
hit that 303-redirect branch first and never exercise the CSRF check.
"""
from __future__ import annotations

import pytest

from app import content as content_module
from app import db as db_module
from tests.conftest import extract_csrf


@pytest.fixture
def seeded_ids():
    conn = db_module.connect()
    try:
        admin_id = conn.execute(
            "SELECT id FROM users WHERE email = 'admin@example.test'"
        ).fetchone()["id"]
        editor_id = conn.execute(
            "SELECT id FROM users WHERE email = 'editor@example.test'"
        ).fetchone()["id"]
    finally:
        conn.close()
    post_id = content_module.create_content("post", "Sweep Post", "sweep-post", "x", admin_id)
    page_id = content_module.create_content("page", "Sweep Page", "sweep-page", "x", admin_id)
    # A real, distinct-from-admin user id for the users.py routes below --
    # not post_id/page_id, which are content ids, not user ids.
    return {"post_id": post_id, "page_id": page_id, "user_id": editor_id}


GET_ROUTES_EDITOR_OR_ADMIN = [
    "/admin", "/admin/content",
    "/admin/posts", "/admin/posts/new", "/admin/posts/{post_id}/edit",
    "/admin/pages", "/admin/pages/new", "/admin/pages/{page_id}/edit",
]
GET_ROUTES_ADMIN_ONLY = ["/admin/users", "/admin/users/new"]
ALL_GET_ROUTES = GET_ROUTES_EDITOR_OR_ADMIN + GET_ROUTES_ADMIN_ONLY

PREVIEW_ROUTES = ["/admin/posts/preview", "/admin/pages/preview"]

# (path template, form body without csrf_token) for every state-changing
# route gated by require_editor_or_admin.
POST_ROUTES_EDITOR_OR_ADMIN = [
    ("/admin/posts/new", {"title": "x", "slug": "x", "body_md": "x"}),
    ("/admin/posts/{post_id}/edit", {"title": "x", "slug": "x", "body_md": "x"}),
    ("/admin/posts/{post_id}/delete", {}),
    ("/admin/posts/{post_id}/revisions/1/rollback", {}),
    ("/admin/pages/new", {"title": "x", "slug": "x", "body_md": "x"}),
    ("/admin/pages/{page_id}/edit", {"title": "x", "slug": "x", "body_md": "x"}),
    ("/admin/pages/{page_id}/delete", {}),
    ("/admin/pages/{page_id}/revisions/1/rollback", {}),
]

# Same shape, but gated by require_admin specifically.
POST_ROUTES_ADMIN_ONLY = [
    ("/admin/posts/{post_id}/publish", {}),
    ("/admin/posts/{post_id}/unpublish", {}),
    ("/admin/pages/{page_id}/publish", {}),
    ("/admin/pages/{page_id}/unpublish", {}),
    ("/admin/users/new", {"email": "sweep-create@example.test", "password": "x", "role": "editor"}),
    ("/admin/users/{user_id}/role", {"role": "editor"}),
    ("/admin/users/{user_id}/deactivate", {}),
]

ALL_STATE_CHANGING_ROUTES = POST_ROUTES_EDITOR_OR_ADMIN + POST_ROUTES_ADMIN_ONLY


# -- 1. anonymous is redirected, never served the page --

@pytest.mark.parametrize("path_template", ALL_GET_ROUTES)
def test_anonymous_is_redirected_on_every_admin_get_route(client, seeded_ids, path_template):
    response = client.get(path_template.format(**seeded_ids), follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


@pytest.mark.parametrize("path_template,body", ALL_STATE_CHANGING_ROUTES)
def test_anonymous_is_redirected_on_every_admin_post_route(client, seeded_ids, path_template, body):
    response = client.post(path_template.format(**seeded_ids), data=body, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


@pytest.mark.parametrize("path", PREVIEW_ROUTES)
def test_anonymous_is_redirected_from_preview_routes(client, path):
    response = client.post(path, data={"body_md": "x"}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


# -- 2. editor gets 403 wherever the route is admin-only --

@pytest.mark.parametrize("path_template", GET_ROUTES_ADMIN_ONLY)
def test_editor_gets_403_on_every_admin_only_get_route(client_as, seeded_ids, path_template):
    response = client_as("editor").get(path_template.format(**seeded_ids))
    assert response.status_code == 403
    assert "Access denied" in response.text


@pytest.mark.parametrize("path_template,body", POST_ROUTES_ADMIN_ONLY)
def test_editor_gets_403_on_every_admin_only_post_route(client_as, seeded_ids, path_template, body):
    editor = client_as("editor")
    csrf = extract_csrf(editor.get("/admin").text)  # any admin page carries one
    response = editor.post(path_template.format(**seeded_ids), data={**body, "csrf_token": csrf})
    assert response.status_code == 403
    assert "Access denied" in response.text


# -- 3. every state-changing form rejects a forged CSRF token --

@pytest.mark.parametrize("path_template,body", ALL_STATE_CHANGING_ROUTES)
def test_every_state_changing_form_rejects_a_forged_csrf_token(
    client_as, seeded_ids, path_template, body,
):
    # Logged in as admin so the 403 can only be the CSRF check, never a role
    # check -- admin passes every role-gated route this diff touches.
    admin = client_as("admin")
    response = admin.post(
        path_template.format(**seeded_ids), data={**body, "csrf_token": "forged-token-value"},
    )
    assert response.status_code == 403
