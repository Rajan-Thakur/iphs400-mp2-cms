"""Post CRUD, publish/unpublish, and live preview — built from the generic
content-CRUD router factory (app/routes/content_crud.py), shared with Pages
(app/routes/pages.py).
"""
from __future__ import annotations

from app.routes.content_crud import build_content_router

KIND = "post"

router = build_content_router(
    kind=KIND, url_prefix="/admin/posts", label="Post", label_plural="Posts",
)
