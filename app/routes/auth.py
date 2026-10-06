"""Login, logout, and the current-user lookup every protected route reuses.

The login form carries a CSRF token like every other state-changing form —
`security.read_or_mint_csrf` works for anonymous requests too, keyed only on
the request's cookies, not on who's logged in.
"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app import db as db_module
from app import security, settings

templates = Jinja2Templates(directory=str(settings.TEMPLATES))
router = APIRouter()


def _render_login(request: Request, error: str | None, status_code: int = 200):
    csrf_token, new_cookie = security.read_or_mint_csrf(request)
    response = templates.TemplateResponse(
        request, "admin/login.html",
        {"title": "Log in", "error": error, "csrf_token": csrf_token},
        status_code=status_code,
    )
    if new_cookie is not None:
        response.set_cookie(security.CSRF_COOKIE, new_cookie, httponly=True, samesite="lax")
    return response


def current_user(request: Request) -> sqlite3.Row | None:
    """The logged-in user's row, or None. Reusable as a FastAPI dependency."""
    uid = security.read_session(request.cookies.get(security.SESSION_COOKIE))
    if uid is None:
        return None
    conn = db_module.connect()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE id = ? AND active = 1", (uid,)
        ).fetchone()
    finally:
        conn.close()


def _user_by_email(email: str) -> sqlite3.Row | None:
    conn = db_module.connect()
    try:
        return conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    finally:
        conn.close()


@router.get("/login")
def login_form(request: Request):
    if current_user(request) is not None:
        return RedirectResponse("/admin", status_code=303)
    return _render_login(request, error=None)


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
):
    if not security.verify_csrf(csrf_token, request.cookies.get(security.CSRF_COOKIE)):
        return _render_login(request, error="Your session expired — please try again.", status_code=403)

    row = _user_by_email(email)
    if row is None or not row["active"] or not security.verify_password(password, row["password_hash"]):
        return _render_login(request, error="Incorrect email or password.", status_code=401)

    response = RedirectResponse("/admin", status_code=303)
    response.set_cookie(
        security.SESSION_COOKIE, security.sign_session(row["id"]),
        httponly=True, samesite="lax", max_age=security.SESSION_MAX_AGE,
    )
    return response


@router.post("/logout")
def logout(request: Request, csrf_token: str = Form(...)):
    if not security.verify_csrf(csrf_token, request.cookies.get(security.CSRF_COOKIE)):
        return _render_login(request, error="Your session expired — please log in again.", status_code=403)
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(security.SESSION_COOKIE)
    return response
