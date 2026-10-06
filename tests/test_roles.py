"""T02: roles and route guards (ticket #3)."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app import guards
from app.guards import NeedsLogin, _require_role


def test_anonymous_is_redirected_to_login(client):
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_editor_can_reach_admin_console(client_as):
    assert client_as("editor").get("/admin").status_code == 200


def test_admin_can_reach_admin_console(client_as):
    assert client_as("admin").get("/admin").status_code == 200


# editor-or-admin's reject path has no test: app/db.py's CHECK constraint only
# allows roles 'admin' and 'editor', so no seedable user can fail that guard.


# -- the public guard functions, exercised directly (current_user stubbed via
#    monkeypatch) so the require_login -> _require_role composition itself is
#    proven correct, not just the private helper in isolation. This covers the
#    admin-only tier ahead of T06, which is the first ticket to wire a route
#    to require_admin. --

def test_require_login_raises_when_anonymous(monkeypatch):
    monkeypatch.setattr(guards, "current_user", lambda request: None)
    with pytest.raises(NeedsLogin):
        guards.require_login(request=None)


def test_require_admin_rejects_editor(monkeypatch):
    monkeypatch.setattr(guards, "current_user", lambda request: {"role": "editor"})
    with pytest.raises(HTTPException) as exc_info:
        guards.require_admin(request=None)
    assert exc_info.value.status_code == 403


def test_require_admin_allows_admin(monkeypatch):
    monkeypatch.setattr(guards, "current_user", lambda request: {"role": "admin"})
    assert guards.require_admin(request=None) == {"role": "admin"}


# -- the private helper itself, as a plain unit test of the role-matching logic --

def test_require_role_allows_a_matching_role():
    user = {"role": "editor"}
    assert _require_role(user, {"editor", "admin"}) is user


def test_require_role_rejects_editor_from_admin_only():
    with pytest.raises(HTTPException) as exc_info:
        _require_role({"role": "editor"}, {"admin"})
    assert exc_info.value.status_code == 403


def test_require_role_allows_admin_through_admin_only():
    user = {"role": "admin"}
    assert _require_role(user, {"admin"}) is user
