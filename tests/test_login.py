"""T01: login and logout (ticket #2)."""
from __future__ import annotations

from app import db as db_module
from app import settings
from tests.conftest import DEMO_USERS, extract_csrf


def _login_csrf(client) -> str:
    return extract_csrf(client.get("/login").text)


def test_admin_can_log_in_and_reach_the_admin_console(client_as):
    c = client_as("admin")
    page = c.get("/admin")
    assert page.status_code == 200
    assert DEMO_USERS["admin"]["email"] in page.text


def test_editor_can_log_in_and_reach_the_admin_console(client_as):
    c = client_as("editor")
    page = c.get("/admin")
    assert page.status_code == 200
    assert DEMO_USERS["editor"]["email"] in page.text


def test_wrong_password_is_refused_with_a_clear_message(client):
    csrf = _login_csrf(client)
    response = client.post(
        "/login",
        data={"email": DEMO_USERS["admin"]["email"], "password": "not-the-real-password",
              "csrf_token": csrf},
    )
    assert response.status_code == 401
    assert "incorrect" in response.text.lower()


def test_email_is_matched_regardless_of_case_and_whitespace(client):
    # T10: accounts are stored lowercased, but login compared the raw input.
    csrf = _login_csrf(client)
    response = client.post(
        "/login",
        data={"email": "  Admin@Example.TEST ", "password": DEMO_USERS["admin"]["password"],
              "csrf_token": csrf},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/admin"


def test_unknown_email_is_refused_the_same_way(client):
    csrf = _login_csrf(client)
    response = client.post(
        "/login", data={"email": "nobody@example.test", "password": "whatever",
                        "csrf_token": csrf},
    )
    assert response.status_code == 401
    assert "incorrect" in response.text.lower()


def test_login_without_csrf_token_is_rejected(client):
    _login_csrf(client)  # just to set the cookie, then deliberately omit the field
    response = client.post(
        "/login",
        data={"email": DEMO_USERS["admin"]["email"], "password": DEMO_USERS["admin"]["password"]},
    )
    assert response.status_code == 422  # missing required form field


def test_login_with_wrong_csrf_token_is_rejected(client):
    _login_csrf(client)
    response = client.post(
        "/login",
        data={"email": DEMO_USERS["admin"]["email"], "password": DEMO_USERS["admin"]["password"],
              "csrf_token": "not-the-real-token"},
    )
    assert response.status_code == 403


def test_logout_clears_the_session(client_as):
    c = client_as("admin")
    assert c.cookies.get("session")

    page = c.get("/admin")
    csrf = extract_csrf(page.text)
    response = c.post("/logout", data={"csrf_token": csrf}, follow_redirects=False)

    assert response.status_code == 303
    assert not c.cookies.get("session")


def test_logout_without_csrf_token_is_rejected(client_as):
    c = client_as("admin")
    response = c.post("/logout", data={}, follow_redirects=False)
    assert response.status_code in (403, 422)
    # the session must still be intact — logout did not happen
    assert c.cookies.get("session")


def test_password_is_stored_as_an_argon2_hash(client_as):
    client_as("admin")  # triggers the autouse seed fixture's db_path
    conn = db_module.connect(settings.DATABASE_PATH)
    try:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE email = ?",
            (DEMO_USERS["admin"]["email"],),
        ).fetchone()
    finally:
        conn.close()
    assert row["password_hash"].startswith("$argon2")
