"""Route-access guards: authenticated, editor-or-admin, admin-only.

FastAPI dependencies can't return a redirect directly, so an anonymous visit
raises NeedsLogin, which create_app() maps to a redirect via an exception
handler. A wrong role raises AccessDenied (a 403) instead — there's nowhere
useful to redirect a logged-in user who simply lacks permission, so
create_app() renders it as an "Access denied" page inside the admin layout.
"""
from __future__ import annotations

import sqlite3

from fastapi import HTTPException, Request

from app import security
from app.routes.auth import current_user
from app.templating import templates


class NeedsLogin(Exception):
    """Raised by require_login() when there's no authenticated user."""


class AccessDenied(HTTPException):
    """Raised when a logged-in user's role doesn't allow the request."""

    def __init__(self, detail: str, user: sqlite3.Row) -> None:
        super().__init__(403, detail=detail)
        self.user = user


def render_access_denied(request: Request, exc: AccessDenied):
    """The exception handler for AccessDenied: a 403 page that keeps the
    admin nav and says why, instead of FastAPI's raw JSON."""
    csrf_token, new_cookie = security.read_or_mint_csrf(request)
    response = templates.TemplateResponse(
        request, "admin/access_denied.html",
        {"title": "Access denied", "current_user": exc.user,
         "csrf_token": csrf_token, "message": exc.detail},
        status_code=403,
    )
    return security.set_csrf_cookie(response, new_cookie)


def _require_role(
    user: sqlite3.Row, allowed_roles: set[str], detail: str | None = None
) -> sqlite3.Row:
    if user["role"] not in allowed_roles:
        raise AccessDenied(
            detail or f"Requires role: {' or '.join(sorted(allowed_roles))}.", user
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
