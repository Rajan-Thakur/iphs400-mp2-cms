"""Shared test fixtures.

`client` gives you the app. `client_as(role)` gives you a client that is logged
in as a seeded user of that role — it works as soon as your login route exists,
so access-control tests stay one line:

    def test_editor_cannot_manage_users(client_as):
        assert client_as("editor").get("/admin/users").status_code in (302, 403)
"""
from __future__ import annotations

import re
import socket
import threading
import time

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
    # settings also reads the developer's own .env; pin the one value tests
    # render, so a title like "Jo's CMS" can't change test outcomes.
    monkeypatch.setattr(settings, "SITE_TITLE", "Test CMS")
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


# --- Browser tests -----------------------------------------------------------
# Layout (does a page fit a 390px phone?) and in-page JavaScript can only be
# checked in a real browser. These fixtures run the app on a local port and
# drive it with Playwright; when Chromium isn't installed
# (`uv run playwright install chromium`), every browser test is skipped.

PHONE_VIEWPORT = {"width": 390, "height": 844}


@pytest.fixture(scope="session")
def live_server():
    """The app on a free localhost port. Tests still get their own database:
    the app reads settings.DATABASE_PATH per request, and the autouse fixture
    above repoints it for every test."""
    import uvicorn

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(), log_level="warning"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        assert time.monotonic() < deadline, "test server did not start"
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)
    sock.close()


@pytest.fixture(scope="session")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as playwright:
        try:
            chromium = playwright.chromium.launch()
        except Exception as exc:  # browser binaries not installed
            pytest.skip(f"Chromium unavailable ({exc.__class__.__name__}); "
                        "run `uv run playwright install chromium`")
        yield chromium
        chromium.close()


@pytest.fixture
def phone(browser, live_server):
    """A fresh 390px-wide browser tab (no cookies) aimed at the test server."""
    context = browser.new_context(viewport=PHONE_VIEWPORT, base_url=live_server)
    yield context.new_page()
    context.close()


def log_in(page, role: str) -> None:
    """Log in through the real login form, as a person would."""
    user = DEMO_USERS[role]
    page.goto("/login")
    page.fill("input[name=email]", user["email"])
    page.fill("input[name=password]", user["password"])
    page.click("button[type=submit]")
    page.wait_for_url("**/admin")
