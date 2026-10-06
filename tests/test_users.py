"""T06: user management (ticket #7)."""
from __future__ import annotations

from app import db as db_module
from app import users as users_module
from tests.conftest import extract_csrf


def _new_user_csrf(client):
    return extract_csrf(client.get("/admin/users/new").text)


def test_admin_can_create_a_new_user(client_as):
    admin = client_as("admin")
    csrf = _new_user_csrf(admin)
    response = admin.post(
        "/admin/users/new",
        data={"email": "newbie@example.test", "password": "a-strong-pw", "role": "editor",
              "csrf_token": csrf},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/users?saved=created"

    conn = db_module.connect()
    try:
        row = conn.execute(
            "SELECT * FROM users WHERE email = 'newbie@example.test'"
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row["role"] == "editor"
    assert row["active"] == 1
    assert row["password_hash"].startswith("$argon2")  # never stored/logged plain


def test_admin_can_change_a_users_role(client_as):
    admin = client_as("admin")
    user_id = next(
        u["id"] for u in users_module.list_users() if u["email"] == "editor@example.test"
    )
    csrf = extract_csrf(admin.get("/admin/users").text)
    response = admin.post(f"/admin/users/{user_id}/role",
                           data={"role": "admin", "csrf_token": csrf}, follow_redirects=False)
    assert response.status_code == 303
    assert users_module.get_user(user_id)["role"] == "admin"


def test_admin_can_deactivate_a_user(client_as):
    admin = client_as("admin")
    user_id = next(
        u["id"] for u in users_module.list_users() if u["email"] == "editor@example.test"
    )
    csrf = extract_csrf(admin.get("/admin/users").text)
    response = admin.post(f"/admin/users/{user_id}/deactivate",
                           data={"csrf_token": csrf}, follow_redirects=False)
    assert response.status_code == 303
    assert users_module.get_user(user_id)["active"] == 0


def test_deactivated_user_login_is_refused_with_a_specific_message(client_as):
    admin = client_as("admin")
    user_id = next(
        u["id"] for u in users_module.list_users() if u["email"] == "editor@example.test"
    )
    csrf = extract_csrf(admin.get("/admin/users").text)
    admin.post(f"/admin/users/{user_id}/deactivate", data={"csrf_token": csrf})

    anon_csrf = extract_csrf(admin.get("/login").text)
    response = admin.post(
        "/login",
        data={"email": "editor@example.test", "password": "test-editor-pw",
              "csrf_token": anon_csrf},
    )
    assert response.status_code == 403
    assert "deactivated" in response.text.lower()


def test_wrong_password_for_a_deactivated_account_still_gets_the_generic_message(client_as):
    # Must not leak account/deactivation state to someone who doesn't already
    # know the correct password.
    admin = client_as("admin")
    user_id = next(
        u["id"] for u in users_module.list_users() if u["email"] == "editor@example.test"
    )
    csrf = extract_csrf(admin.get("/admin/users").text)
    admin.post(f"/admin/users/{user_id}/deactivate", data={"csrf_token": csrf})

    login_csrf = extract_csrf(admin.get("/login").text)
    response = admin.post(
        "/login",
        data={"email": "editor@example.test", "password": "wrong-password",
              "csrf_token": login_csrf},
    )
    assert response.status_code == 401
    assert "incorrect" in response.text.lower()
    assert "deactivated" not in response.text.lower()


def test_editor_is_refused_on_every_user_management_route(client_as):
    editor = client_as("editor")
    other_id = next(
        u["id"] for u in users_module.list_users() if u["email"] == "admin@example.test"
    )
    assert editor.get("/admin/users").status_code == 403
    assert editor.get("/admin/users/new").status_code == 403
    assert editor.post("/admin/users/new", data={
        "email": "x@example.test", "password": "x", "role": "editor", "csrf_token": "x",
    }).status_code == 403
    assert editor.post(f"/admin/users/{other_id}/role", data={
        "role": "editor", "csrf_token": "x",
    }).status_code == 403
    assert editor.post(f"/admin/users/{other_id}/deactivate", data={
        "csrf_token": "x",
    }).status_code == 403


def test_create_user_rejects_wrong_csrf(client_as):
    admin = client_as("admin")
    response = admin.post(
        "/admin/users/new",
        data={"email": "x@example.test", "password": "x", "role": "editor",
              "csrf_token": "wrong"},
    )
    assert response.status_code == 403
    conn = db_module.connect()
    try:
        row = conn.execute("SELECT * FROM users WHERE email = 'x@example.test'").fetchone()
    finally:
        conn.close()
    assert row is None


def test_create_user_rejects_duplicate_email(client_as):
    admin = client_as("admin")
    csrf = _new_user_csrf(admin)
    response = admin.post(
        "/admin/users/new",
        data={"email": "editor@example.test", "password": "whatever", "role": "editor",
              "csrf_token": csrf},
    )
    assert response.status_code == 200
    assert "already in use" in response.text.lower()


def test_change_role_rejects_wrong_csrf(client_as):
    admin = client_as("admin")
    user_id = next(
        u["id"] for u in users_module.list_users() if u["email"] == "editor@example.test"
    )
    response = admin.post(f"/admin/users/{user_id}/role",
                           data={"role": "admin", "csrf_token": "wrong"})
    assert response.status_code == 403
    assert users_module.get_user(user_id)["role"] == "editor"


def test_deactivate_rejects_wrong_csrf(client_as):
    admin = client_as("admin")
    user_id = next(
        u["id"] for u in users_module.list_users() if u["email"] == "editor@example.test"
    )
    response = admin.post(f"/admin/users/{user_id}/deactivate",
                           data={"csrf_token": "wrong"})
    assert response.status_code == 403
    assert users_module.get_user(user_id)["active"] == 1


def test_admin_cannot_change_their_own_role(client_as):
    admin = client_as("admin")
    self_id = next(
        u["id"] for u in users_module.list_users() if u["email"] == "admin@example.test"
    )
    csrf = extract_csrf(admin.get("/admin/users").text)
    response = admin.post(f"/admin/users/{self_id}/role",
                           data={"role": "editor", "csrf_token": csrf})
    assert response.status_code == 403
    assert "own role" in response.text.lower()
    assert users_module.get_user(self_id)["role"] == "admin"


def test_admin_cannot_deactivate_their_own_account(client_as):
    admin = client_as("admin")
    self_id = next(
        u["id"] for u in users_module.list_users() if u["email"] == "admin@example.test"
    )
    csrf = extract_csrf(admin.get("/admin/users").text)
    response = admin.post(f"/admin/users/{self_id}/deactivate", data={"csrf_token": csrf})
    assert response.status_code == 403
    assert "own account" in response.text.lower()
    assert users_module.get_user(self_id)["active"] == 1


def test_create_user_rejects_an_invalid_email(client_as):
    admin = client_as("admin")
    csrf = _new_user_csrf(admin)
    response = admin.post(
        "/admin/users/new",
        data={"email": "not-an-email", "password": "whatever", "role": "editor",
              "csrf_token": csrf},
    )
    assert response.status_code == 200
    assert "valid email" in response.text.lower()
    conn = db_module.connect()
    try:
        row = conn.execute("SELECT * FROM users WHERE email = 'not-an-email'").fetchone()
    finally:
        conn.close()
    assert row is None


def test_anonymous_is_redirected_from_users_list(client):
    response = client.get("/admin/users", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
