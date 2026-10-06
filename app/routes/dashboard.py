"""The admin dashboard: content counts by status, and a combined,
filterable content list across Posts and Pages (ticket T08).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.templating import Jinja2Templates

from app import content as content_module
from app import security, settings
from app.guards import require_editor_or_admin
from app.routes import pages as pages_module
from app.routes import posts as posts_module

templates = Jinja2Templates(directory=str(settings.TEMPLATES))
router = APIRouter()

VALID_STATUSES = {content_module.STATUS_DRAFT, content_module.STATUS_PUBLISHED}
EDIT_URL_PREFIX = {posts_module.KIND: posts_module.URL_PREFIX,
                   pages_module.KIND: pages_module.URL_PREFIX}
VALID_KINDS = set(EDIT_URL_PREFIX)


@router.get("/admin")
def dashboard(request: Request, user=Depends(require_editor_or_admin)):
    csrf_token, new_cookie = security.read_or_mint_csrf(request)
    response = templates.TemplateResponse(
        request, "admin/dashboard.html",
        {"title": "Admin", "current_user": user, "csrf_token": csrf_token,
         "counts": content_module.count_by_status()},
    )
    return security.set_csrf_cookie(response, new_cookie)


@router.get("/admin/content")
def content_overview(
    request: Request,
    status: str | None = Query(None),
    content_type: str | None = Query(None, alias="type"),
    user=Depends(require_editor_or_admin),
):
    status_filter = status if status in VALID_STATUSES else None
    kind_filter = content_type if content_type in VALID_KINDS else None
    items = content_module.list_filtered(status=status_filter, kind=kind_filter)
    csrf_token, new_cookie = security.read_or_mint_csrf(request)
    response = templates.TemplateResponse(
        request, "admin/content_overview.html",
        {"title": "All content", "current_user": user, "csrf_token": csrf_token,
         "items": items, "status_filter": status_filter or "all",
         "type_filter": kind_filter or "all", "edit_url_prefix": EDIT_URL_PREFIX},
    )
    return security.set_csrf_cookie(response, new_cookie)
