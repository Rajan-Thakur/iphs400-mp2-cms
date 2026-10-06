"""The FastAPI application.

The admin console lives under /admin; the public site is served at the same
paths the static export writes. Routes live in their own modules under
app/routes/ and are included here. Keep this file small.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from app.guards import AccessDenied, NeedsLogin, render_access_denied
from app.routes import auth, dashboard, pages, posts, public, users


def create_app() -> FastAPI:
    app = FastAPI(title="IPHS 400 MP2 CMS")
    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(posts.router)
    app.include_router(pages.router)
    app.include_router(users.router)
    app.include_router(public.router)  # last: its /{slug}.html matches broadly

    @app.exception_handler(NeedsLogin)
    def _redirect_to_login(request: Request, exc: NeedsLogin):
        return RedirectResponse("/login", status_code=303)

    app.add_exception_handler(AccessDenied, render_access_denied)

    return app


app = create_app()
