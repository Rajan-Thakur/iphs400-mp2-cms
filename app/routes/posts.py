"""Post CRUD (create, edit, delete) and a live Markdown preview.

Editors and Admins share full CRUD here, including deleting another editor's
post — publish/unpublish is an Admin-only action that arrives in a later
ticket. Pages (T05) will reuse this same table and most of this logic,
distinguished only by kind='page'.
"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app import content as content_module
from app import security, settings
from app.guards import require_editor_or_admin
from app.mdrender import render_markdown

templates = Jinja2Templates(directory=str(settings.TEMPLATES))
router = APIRouter(prefix="/admin/posts")

KIND = "post"


def _render_form(request, user, *, post, title, slug, body_md, error, status_code=200):
    csrf_token, new_cookie = security.read_or_mint_csrf(request)
    response = templates.TemplateResponse(
        request, "admin/post_form.html",
        {
            "title": "Edit post" if post else "New post",
            "current_user": user,
            "csrf_token": csrf_token,
            "post": post,
            "form_title": title,
            "form_slug": slug,
            "form_body_md": body_md,
            "preview_html": render_markdown(body_md),
            "error": error,
        },
        status_code=status_code,
    )
    return security.set_csrf_cookie(response, new_cookie)


def _csrf_error(request, user, *, post, title, slug, body_md):
    return _render_form(
        request, user, post=post, title=title, slug=slug, body_md=body_md,
        error="Your session expired — please try again.", status_code=403,
    )


def _render_post_list(request, user, *, saved=None, error=None, status_code=200):
    posts = content_module.list_content(KIND)
    csrf_token, new_cookie = security.read_or_mint_csrf(request)
    response = templates.TemplateResponse(
        request, "admin/post_list.html",
        {"title": "Posts", "current_user": user, "posts": posts,
         "csrf_token": csrf_token, "saved": saved, "error": error},
        status_code=status_code,
    )
    return security.set_csrf_cookie(response, new_cookie)


def _save_post(request, user, *, post, title, slug, body_md, redirect_saved_as):
    """Shared by create and update: validate the slug, write the row, and
    turn an IntegrityError (duplicate slug) into a form error instead of a
    500. `post` is None for create, the existing row for update."""
    normalized_slug = content_module.validate_slug(slug)
    if normalized_slug is None:
        return _render_form(
            request, user, post=post, title=title, slug=slug, body_md=body_md,
            error="Slug must be lowercase letters, numbers, and hyphens only.",
        )
    try:
        if post is None:
            content_module.create_content(KIND, title, normalized_slug, body_md, user["id"])
        else:
            content_module.update_content(post["id"], KIND, title, normalized_slug, body_md)
    except sqlite3.IntegrityError:
        return _render_form(
            request, user, post=post, title=title, slug=slug, body_md=body_md,
            error="That slug is already used by another post.",
        )
    return RedirectResponse(f"/admin/posts?saved={redirect_saved_as}", status_code=303)


@router.get("")
def list_posts(request: Request, user=Depends(require_editor_or_admin)):
    return _render_post_list(request, user, saved=request.query_params.get("saved"))


@router.get("/new")
def new_post_form(request: Request, user=Depends(require_editor_or_admin)):
    return _render_form(request, user, post=None, title="", slug="", body_md="", error=None)


@router.post("/new")
def create_post(
    request: Request,
    title: str = Form(...),
    slug: str = Form(...),
    body_md: str = Form(""),
    csrf_token: str = Form(...),
    user=Depends(require_editor_or_admin),
):
    if not security.verify_csrf(csrf_token, request.cookies.get(security.CSRF_COOKIE)):
        return _csrf_error(request, user, post=None, title=title, slug=slug, body_md=body_md)
    return _save_post(request, user, post=None, title=title, slug=slug, body_md=body_md,
                       redirect_saved_as="created")


@router.get("/{post_id}/edit")
def edit_post_form(request: Request, post_id: int, user=Depends(require_editor_or_admin)):
    post = content_module.get_content(post_id, KIND)
    if post is None:
        return RedirectResponse("/admin/posts", status_code=303)
    return _render_form(
        request, user, post=post, title=post["title"], slug=post["slug"],
        body_md=post["body_md"], error=None,
    )


@router.post("/{post_id}/edit")
def update_post(
    request: Request,
    post_id: int,
    title: str = Form(...),
    slug: str = Form(...),
    body_md: str = Form(""),
    csrf_token: str = Form(...),
    user=Depends(require_editor_or_admin),
):
    post = content_module.get_content(post_id, KIND)
    if post is None:
        return RedirectResponse("/admin/posts", status_code=303)
    if not security.verify_csrf(csrf_token, request.cookies.get(security.CSRF_COOKIE)):
        return _csrf_error(request, user, post=post, title=title, slug=slug, body_md=body_md)
    return _save_post(request, user, post=post, title=title, slug=slug, body_md=body_md,
                       redirect_saved_as="updated")


@router.post("/{post_id}/delete")
def delete_post(
    request: Request,
    post_id: int,
    csrf_token: str = Form(...),
    user=Depends(require_editor_or_admin),
):
    if not security.verify_csrf(csrf_token, request.cookies.get(security.CSRF_COOKIE)):
        return _render_post_list(
            request, user, error="Your session expired — please try again.", status_code=403,
        )
    content_module.delete_content(post_id, KIND)
    return RedirectResponse("/admin/posts?saved=deleted", status_code=303)


@router.post("/preview")
def preview_post(body_md: str = Form(""), user=Depends(require_editor_or_admin)):
    """Render+sanitize arbitrary Markdown for the live preview pane. No
    CSRF check: this has no side effect, it only echoes back sanitized HTML."""
    return HTMLResponse(render_markdown(body_md))
