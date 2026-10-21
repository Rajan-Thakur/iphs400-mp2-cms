"""The Media library (MP2plus F1, issue #21): Editors and Admins upload PNG
and JPEG images with Alt text and copy each one's Markdown snippet into a
Post. The admin server also serves media/ to logged-in users, so the
library's images and the editor's preview show.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse

from app import media as media_module
from app import security
from app.guards import require_editor_or_admin
from app.templating import templates

router = APIRouter()

LIBRARY_TEMPLATE = "admin/media_library.html"
CSRF_EXPIRED_MESSAGE = "Your session expired — please try again."


def _render_library(request, user, *, saved=None, error=None, form_alt="", status_code=200):
    items = [{**item, "snippet": media_module.snippet(item)} for item in media_module.list_media()]
    csrf_token, new_cookie = security.read_or_mint_csrf(request)
    response = templates.TemplateResponse(
        request, LIBRARY_TEMPLATE,
        {"title": "Media", "current_user": user, "csrf_token": csrf_token,
         "items": items, "saved": saved, "error": error, "form_alt": form_alt},
        status_code=status_code,
    )
    return security.set_csrf_cookie(response, new_cookie)


@router.get("/admin/media")
def media_library(request: Request, user=Depends(require_editor_or_admin)):
    return _render_library(request, user, saved=request.query_params.get("saved"))


@router.post("/admin/media/upload")
def upload_media(
    request: Request,
    image: UploadFile | None = File(None),
    alt_text: str = Form(""),
    csrf_token: str = Form(""),
    user=Depends(require_editor_or_admin),
):
    # Every field defaults to empty rather than being required, so a POST
    # missing its token (or its file) gets this page's message, not a 422.
    if not security.verify_csrf(csrf_token, request.cookies.get(security.CSRF_COOKIE)):
        return _render_library(request, user, error=CSRF_EXPIRED_MESSAGE, form_alt=alt_text,
                               status_code=403)
    filename = image.filename if image else ""
    # One byte past the limit is enough to know a file is too big.
    data = image.file.read(media_module.MAX_BYTES + 1) if image else b""
    try:
        media_module.save_upload(filename, data, alt_text, user["id"])
    except media_module.UploadRefused as refused:
        return _render_library(request, user, error=str(refused), form_alt=alt_text,
                               status_code=400)
    return RedirectResponse("/admin/media?saved=uploaded", status_code=303)


@router.get("/media/{filename}")
def media_file(filename: str, user=Depends(require_editor_or_admin)):
    path = media_module.served_file(filename)
    if path is None:
        raise HTTPException(404)
    return FileResponse(path, headers={"X-Content-Type-Options": "nosniff"})
