"""Page CRUD, publish/unpublish, and live preview — the same logic Posts
have (app/routes/posts.py), built from the generic content-CRUD router
factory (app/routes/content_crud.py). A published Page also appears in the
public site's navigation — see app/publish.py and app/main.py.
"""
from __future__ import annotations

from app.routes.content_crud import build_content_router

KIND = "page"
URL_PREFIX = "/admin/pages"

router = build_content_router(
    kind=KIND, url_prefix=URL_PREFIX, label="Page", label_plural="Pages",
)
