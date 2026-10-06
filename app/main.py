"""The FastAPI application.

T00 (already done): the admin console answers at /admin and the public site
answers at /. That is the whole skeleton — it exists so you can prove the stack
runs before you build anything on it.

Add your routes in their own modules (app/routes/posts.py and so on) and include
them here. Keep this file small.
"""
from __future__ import annotations

from fastapi import FastAPI, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app import settings
from app.guards import NeedsLogin
from app.publish import CSS, nav_items
from app.routes import auth, dashboard, pages, posts, users

templates = Jinja2Templates(directory=str(settings.TEMPLATES))


def create_app() -> FastAPI:
    app = FastAPI(title="IPHS 400 MP2 CMS")
    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(posts.router)
    app.include_router(pages.router)
    app.include_router(users.router)

    @app.exception_handler(NeedsLogin)
    def _redirect_to_login(request: Request, exc: NeedsLogin):
        return RedirectResponse("/login", status_code=303)

    @app.get("/")
    def public_home(request: Request):
        return templates.TemplateResponse(
            request, "public/home.html",
            {"title": settings.SITE_TITLE, "items": [], "nav_items": nav_items()},
        )

    @app.get("/style.css")
    def style_css():
        return Response(CSS, media_type="text/css")

    return app


app = create_app()
