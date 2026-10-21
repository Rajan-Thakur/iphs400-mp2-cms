"""The admin-only Settings page (MP2plus F8, issue #23): an Admin picks the
site's Theme. The choice is stored in the database, so it survives a
restart; the admin console shows it on the next page load, and the public
site gets it on the next `cms publish`.
"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app import security
from app import theme as theme_module
from app.guards import require_admin
from app.templating import templates

router = APIRouter(prefix="/admin/settings")

CSRF_EXPIRED_MESSAGE = "Your session expired — please try again."
UNKNOWN_THEME_MESSAGE = "Pick one of the themes listed."


def _require_admin_for_settings(request: Request) -> sqlite3.Row:
    return require_admin(request, detail="Only an Admin can change the site's settings.")


def _render(request, user, *, saved=None, error=None, status_code=200):
    csrf_token, new_cookie = security.read_or_mint_csrf(request)
    response = templates.TemplateResponse(
        request, "admin/settings.html",
        {"title": "Settings", "current_user": user, "csrf_token": csrf_token,
         "themes": theme_module.available(), "selected_theme": theme_module.selected(),
         "saved": saved, "error": error},
        status_code=status_code,
    )
    return security.set_csrf_cookie(response, new_cookie)


@router.get("")
def settings_page(request: Request, user=Depends(_require_admin_for_settings)):
    return _render(request, user, saved=request.query_params.get("saved"))


@router.post("")
def save_settings(
    request: Request,
    theme: str = Form(""),
    csrf_token: str = Form(""),
    user=Depends(_require_admin_for_settings),
):
    # Fields default to empty rather than being required, so a POST missing
    # its token gets this page's message, not a 422.
    if not security.verify_csrf(csrf_token, request.cookies.get(security.CSRF_COOKIE)):
        return _render(request, user, error=CSRF_EXPIRED_MESSAGE, status_code=403)
    try:
        theme_module.select(theme)
    except theme_module.UnknownTheme:
        return _render(request, user, error=UNKNOWN_THEME_MESSAGE, status_code=400)
    return RedirectResponse("/admin/settings?saved=theme", status_code=303)
