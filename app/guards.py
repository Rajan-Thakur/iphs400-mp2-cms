"""Route-access guards: authenticated, editor-or-admin, admin-only.

FastAPI dependencies can't return a redirect directly, so an anonymous visit
raises NeedsLogin, which create_app() maps to a redirect via an exception
handler. A wrong role raises a plain HTTPException(403) instead — there's
nowhere useful to redirect a logged-in user who simply lacks permission.
"""
from __future__ import annotations

import sqlite3

from fastapi import HTTPException, Request

from app.routes.auth import current_user


class NeedsLogin(Exception):
    """Raised by require_login() when there's no authenticated user."""


def _require_role(
    user: sqlite3.Row, allowed_roles: set[str], detail: str | None = None
) -> sqlite3.Row:
    if user["role"] not in allowed_roles:
        raise HTTPException(
            403, detail=detail or f"Requires role: {' or '.join(sorted(allowed_roles))}."
        )
    return user


def require_login(request: Request) -> sqlite3.Row:
    user = current_user(request)
    if user is None:
        raise NeedsLogin()
    return user


def require_editor_or_admin(request: Request) -> sqlite3.Row:
    return _require_role(require_login(request), {"editor", "admin"})


def require_admin(request: Request, detail: str | None = None) -> sqlite3.Row:
    """`detail` lets a specific route explain the actual reason for the 403
    (e.g. "only an Admin can publish") instead of the generic role message."""
    return _require_role(require_login(request), {"admin"}, detail=detail)
