"""Admin-only user management: create an account, change a role, deactivate
(ticket T06). Reuses T02's require_admin guard — an Editor gets a plain 403
on every route here.
"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app import security, settings
from app import users as users_module
from app.guards import require_admin

templates = Jinja2Templates(directory=str(settings.TEMPLATES))
router = APIRouter(prefix="/admin/users")

CSRF_EXPIRED_MESSAGE = "Your session expired — please try again."


def _render_list(request, user, *, error=None, saved=None, status_code=200):
    users = users_module.list_users()
    csrf_token, new_cookie = security.read_or_mint_csrf(request)
    response = templates.TemplateResponse(
        request, "admin/user_list.html",
        {"title": "Users", "current_user": user, "users": users,
         "csrf_token": csrf_token, "error": error, "saved": saved},
        status_code=status_code,
    )
    return security.set_csrf_cookie(response, new_cookie)


def _render_new_form(request, user, *, error=None, form_email="", form_role="editor",
                      status_code=200):
    csrf_token, new_cookie = security.read_or_mint_csrf(request)
    response = templates.TemplateResponse(
        request, "admin/user_form.html",
        {"title": "New user", "current_user": user, "csrf_token": csrf_token,
         "error": error, "form_email": form_email, "form_role": form_role},
        status_code=status_code,
    )
    return security.set_csrf_cookie(response, new_cookie)


def _csrf_error_list(request, user):
    return _render_list(request, user, error=CSRF_EXPIRED_MESSAGE, status_code=403)


def _csrf_error_new_form(request, user, *, form_email, form_role):
    return _render_new_form(
        request, user, error=CSRF_EXPIRED_MESSAGE,
        form_email=form_email, form_role=form_role, status_code=403,
    )


def _validate_role(role: str) -> str | None:
    """Return an error message if `role` isn't valid, else None."""
    return None if role in users_module.ROLES else "Role must be admin or editor."


@router.get("")
def list_users_route(request: Request, user=Depends(require_admin)):
    return _render_list(request, user, saved=request.query_params.get("saved"))


@router.get("/new")
def new_user_form(request: Request, user=Depends(require_admin)):
    return _render_new_form(request, user)


@router.post("/new")
def create_user_route(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    csrf_token: str = Form(...),
    user=Depends(require_admin),
):
    if not security.verify_csrf(csrf_token, request.cookies.get(security.CSRF_COOKIE)):
        return _csrf_error_new_form(request, user, form_email=email, form_role=role)

    role_error = _validate_role(role)
    if role_error:
        return _render_new_form(request, user, error=role_error, form_email=email, form_role=role)

    normalized_email = users_module.validate_email(email)
    if normalized_email is None:
        return _render_new_form(
            request, user, error="That doesn't look like a valid email address.",
            form_email=email, form_role=role,
        )
    try:
        users_module.create_user(normalized_email, password, role)
    except sqlite3.IntegrityError:
        return _render_new_form(
            request, user, error="That email is already in use.",
            form_email=email, form_role=role,
        )
    return RedirectResponse("/admin/users?saved=created", status_code=303)


@router.post("/{user_id}/role")
def change_role(
    request: Request,
    user_id: int,
    role: str = Form(...),
    csrf_token: str = Form(...),
    user=Depends(require_admin),
):
    if not security.verify_csrf(csrf_token, request.cookies.get(security.CSRF_COOKIE)):
        return _csrf_error_list(request, user)
    if user_id == user["id"]:
        return _render_list(
            request, user, error="You can't change your own role — ask another Admin.",
            status_code=403,
        )
    role_error = _validate_role(role)
    if role_error:
        return _render_list(request, user, error=role_error)
    target = users_module.get_user(user_id)
    if target is None:
        return RedirectResponse("/admin/users", status_code=303)
    users_module.set_role(user_id, role)
    return RedirectResponse("/admin/users?saved=role-changed", status_code=303)


@router.post("/{user_id}/deactivate")
def deactivate_user_route(
    request: Request,
    user_id: int,
    csrf_token: str = Form(...),
    user=Depends(require_admin),
):
    if not security.verify_csrf(csrf_token, request.cookies.get(security.CSRF_COOKIE)):
        return _csrf_error_list(request, user)
    if user_id == user["id"]:
        return _render_list(
            request, user, error="You can't deactivate your own account — ask another Admin.",
            status_code=403,
        )
    target = users_module.get_user(user_id)
    if target is None:
        return RedirectResponse("/admin/users", status_code=303)
    users_module.deactivate_user(user_id)
    return RedirectResponse("/admin/users?saved=deactivated", status_code=303)
