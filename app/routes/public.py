"""The public site, served live by the dev server at the same paths the static
export writes (index.html, posts/<slug>.html, <slug>.html, and search.html with
its search.js and search-index.json). Both render through app.publish, so the
local preview and the deployed site can't drift.
Only published content is ever served; a draft's URL is a 404.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, Response

from app import content as content_module
from app.publish import (
    CSS, SEARCH_JS, home_html, page_html, post_html, search_html, search_index_json,
)

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
@router.get("/index.html", response_class=HTMLResponse)
def home():
    return home_html()


@router.get("/style.css")
def style_css():
    return Response(CSS, media_type="text/css")


@router.get("/search.html", response_class=HTMLResponse)
def search_page():
    return search_html()


@router.get("/search.js")
def search_js():
    return Response(SEARCH_JS, media_type="text/javascript")


@router.get("/search-index.json")
def search_index():
    return Response(search_index_json(), media_type="application/json")


@router.get("/posts/{slug}.html", response_class=HTMLResponse)
def public_post(slug: str):
    post = content_module.get_published_by_slug("post", slug)
    if post is None:
        raise HTTPException(404)
    return post_html(post)


@router.get("/{slug}.html", response_class=HTMLResponse)
def public_page(slug: str):
    page = content_module.get_published_by_slug("page", slug)
    if page is None:
        raise HTTPException(404)
    return page_html(page)
