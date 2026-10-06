"""Shared test fixtures.

`client` gives you the app. `client_as(role)` gives you a client that is logged
in as a seeded user of that role — it works as soon as your login route exists,
so access-control tests stay one line:

    def test_editor_cannot_manage_users(client_as):
        assert client_as("editor").get("/admin/users").status_code in (302, 403)
"""
from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app import settings
from app.main import create_app
from app.seed import seed_users


def extract_csrf(html: str) -> str:
    """Pull the csrf_token hidden-field value out of a rendered admin page."""
    match = re.search(r'name="csrf_token" value="([^"]*)"', html)
    assert match, "expected a csrf_token hidden field in the rendered page"
    return match.group(1)

# Matches scripts/seed_demo.py. Passwords come from the environment there; in
# tests they are fixed and meaningless.
DEMO_USERS = {
    "admin": {"email": "admin@example.test", "password": "test-admin-pw"},
    "editor": {"email": "editor@example.test", "password": "test-editor-pw"},
}


@pytest.fixture(autouse=True)
def _isolated_seeded_db(monkeypatch, tmp_path):
    """Every test gets its own temp SQLite file, pre-seeded with the two
    demo users above, so tests never touch the real dev database and never
    see state left over from another test."""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(settings, "DATABASE_PATH", db_path)
    seed_users(db_path, DEMO_USERS["admin"]["password"], DEMO_USERS["editor"]["password"])
    yield db_path


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


@pytest.fixture
def client_as():
    """Return a factory: client_as("editor") -> a logged-in TestClient."""

    def _login(role: str) -> TestClient:
        user = DEMO_USERS[role]
        c = TestClient(create_app())
        login_page = c.get("/login")
        if login_page.status_code == 404:
            pytest.skip("No /login route yet — build the login ticket first.")
        csrf_token = extract_csrf(login_page.text)
        response = c.post("/login", data={"email": user["email"],
                                          "password": user["password"],
                                          "csrf_token": csrf_token},
                          follow_redirects=False)
        assert response.status_code in (200, 302, 303), (
            f"Login as {role} failed with {response.status_code}")
        return c

    return _login
