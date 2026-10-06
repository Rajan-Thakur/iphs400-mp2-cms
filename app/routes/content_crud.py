"""Generic CRUD + publish/unpublish + live-preview routes for one content
`kind`. Posts and Pages share the same table and almost all of this logic
(see CONTEXT.md) — only the kind, URL prefix, and display label differ, so
`posts.py` and `pages.py` are each a few lines that call `build_content_router`.
"""
from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app import content as content_module
from app import security, settings
from app.guards import require_admin, require_editor_or_admin
from app.mdrender import render_markdown

templates = Jinja2Templates(directory=str(settings.TEMPLATES))

LIST_TEMPLATE = "admin/content_list.html"
FORM_TEMPLATE = "admin/content_form.html"


def build_content_router(*, kind: str, url_prefix: str, label: str, label_plural: str) -> APIRouter:
    router = APIRouter(prefix=url_prefix)
    publish_detail = (
        f"Only an Admin can publish or unpublish a {label} — ask an Admin to do this for you."
    )

    def _require_admin_to_publish(request: Request):
        return require_admin(request, detail=publish_detail)

    def _render_form(request, user, *, item, title, slug, body_md, error, status_code=200):
        csrf_token, new_cookie = security.read_or_mint_csrf(request)
        response = templates.TemplateResponse(
            request, FORM_TEMPLATE,
            {
                "title": f"Edit {label}" if item else f"New {label}",
                "current_user": user,
                "csrf_token": csrf_token,
                "item": item,
                "url_prefix": url_prefix,
                "form_title": title,
                "form_slug": slug,
                "form_body_md": body_md,
                "preview_html": render_markdown(body_md),
                "error": error,
            },
            status_code=status_code,
        )
        return security.set_csrf_cookie(response, new_cookie)

    def _csrf_error(request, user, *, item, title, slug, body_md):
        return _render_form(
            request, user, item=item, title=title, slug=slug, body_md=body_md,
            error="Your session expired — please try again.", status_code=403,
        )

    def _render_list(request, user, *, saved=None, error=None, status_code=200):
        items = content_module.list_content(kind)
        csrf_token, new_cookie = security.read_or_mint_csrf(request)
        response = templates.TemplateResponse(
            request, LIST_TEMPLATE,
            {"title": label_plural, "label": label, "label_plural": label_plural,
             "url_prefix": url_prefix, "current_user": user, "items": items,
             "csrf_token": csrf_token, "saved": saved, "error": error,
             "is_admin": user["role"] == "admin"},
            status_code=status_code,
        )
        return security.set_csrf_cookie(response, new_cookie)

    def _save(request, user, *, item, title, slug, body_md, redirect_saved_as):
        """Shared by create and update: validate the slug, write the row,
        and turn an IntegrityError (duplicate slug) into a form error
        instead of a 500. `item` is None for create, the existing row for
        update."""
        normalized_slug = content_module.validate_slug(slug)
        if normalized_slug is None:
            return _render_form(
                request, user, item=item, title=title, slug=slug, body_md=body_md,
                error="Slug must be lowercase letters, numbers, and hyphens only.",
            )
        reserved_for = content_module.reserved_slug_reason(kind, normalized_slug)
        if reserved_for:
            return _render_form(
                request, user, item=item, title=title, slug=slug, body_md=body_md,
                error=f'"{normalized_slug}" is reserved for {reserved_for} — choose another slug.',
            )
        try:
            if item is None:
                content_module.create_content(kind, title, normalized_slug, body_md, user["id"])
            else:
                content_module.update_content(item["id"], kind, title, normalized_slug, body_md)
        except sqlite3.IntegrityError:
            return _render_form(
                request, user, item=item, title=title, slug=slug, body_md=body_md,
                error=f"That slug is already used by another {label.lower()}.",
            )
        return RedirectResponse(f"{url_prefix}?saved={redirect_saved_as}", status_code=303)

    def _apply_status_change(request, user, item_id, *, new_status, saved_as, csrf_token):
        if not security.verify_csrf(csrf_token, request.cookies.get(security.CSRF_COOKIE)):
            return _render_list(
                request, user, error="Your session expired — please try again.", status_code=403,
            )
        item = content_module.get_content(item_id, kind)
        if item is None:
            return RedirectResponse(url_prefix, status_code=303)
        content_module.set_status(item_id, kind, new_status)
        return RedirectResponse(f"{url_prefix}?saved={saved_as}", status_code=303)

    @router.get("")
    def list_items(request: Request, user=Depends(require_editor_or_admin)):
        return _render_list(request, user, saved=request.query_params.get("saved"))

    @router.get("/new")
    def new_item_form(request: Request, user=Depends(require_editor_or_admin)):
        return _render_form(request, user, item=None, title="", slug="", body_md="", error=None)

    @router.post("/new")
    def create_item(
        request: Request,
        title: str = Form(...),
        slug: str = Form(...),
        body_md: str = Form(""),
        csrf_token: str = Form(...),
        user=Depends(require_editor_or_admin),
    ):
        if not security.verify_csrf(csrf_token, request.cookies.get(security.CSRF_COOKIE)):
            return _csrf_error(request, user, item=None, title=title, slug=slug, body_md=body_md)
        return _save(request, user, item=None, title=title, slug=slug, body_md=body_md,
                     redirect_saved_as="created")

    @router.get("/{item_id}/edit")
    def edit_item_form(request: Request, item_id: int, user=Depends(require_editor_or_admin)):
        item = content_module.get_content(item_id, kind)
        if item is None:
            return RedirectResponse(url_prefix, status_code=303)
        return _render_form(
            request, user, item=item, title=item["title"], slug=item["slug"],
            body_md=item["body_md"], error=None,
        )

    @router.post("/{item_id}/edit")
    def update_item(
        request: Request,
        item_id: int,
        title: str = Form(...),
        slug: str = Form(...),
        body_md: str = Form(""),
        csrf_token: str = Form(...),
        user=Depends(require_editor_or_admin),
    ):
        item = content_module.get_content(item_id, kind)
        if item is None:
            return RedirectResponse(url_prefix, status_code=303)
        if not security.verify_csrf(csrf_token, request.cookies.get(security.CSRF_COOKIE)):
            return _csrf_error(request, user, item=item, title=title, slug=slug, body_md=body_md)
        return _save(request, user, item=item, title=title, slug=slug, body_md=body_md,
                     redirect_saved_as="updated")

    @router.post("/{item_id}/delete")
    def delete_item(
        request: Request,
        item_id: int,
        csrf_token: str = Form(...),
        user=Depends(require_editor_or_admin),
    ):
        if not security.verify_csrf(csrf_token, request.cookies.get(security.CSRF_COOKIE)):
            return _render_list(
                request, user, error="Your session expired — please try again.", status_code=403,
            )
        content_module.delete_content(item_id, kind)
        return RedirectResponse(f"{url_prefix}?saved=deleted", status_code=303)

    @router.post("/{item_id}/publish")
    def publish_item(
        request: Request, item_id: int, csrf_token: str = Form(...),
        user=Depends(_require_admin_to_publish),
    ):
        return _apply_status_change(
            request, user, item_id, new_status=content_module.STATUS_PUBLISHED,
            saved_as="published", csrf_token=csrf_token,
        )

    @router.post("/{item_id}/unpublish")
    def unpublish_item(
        request: Request, item_id: int, csrf_token: str = Form(...),
        user=Depends(_require_admin_to_publish),
    ):
        return _apply_status_change(
            request, user, item_id, new_status=content_module.STATUS_DRAFT,
            saved_as="unpublished", csrf_token=csrf_token,
        )

    @router.post("/preview")
    def preview_item(body_md: str = Form(""), user=Depends(require_editor_or_admin)):
        """Render+sanitize arbitrary Markdown for the live preview pane. No
        CSRF check: this has no side effect, it only echoes back sanitized HTML."""
        return HTMLResponse(render_markdown(body_md))

    return router
