"""The FastAPI application.

T00 (already done): the admin console answers at /admin and the public site
answers at /. That is the whole skeleton — it exists so you can prove the stack
runs before you build anything on it.

Add your routes in their own modules (app/routes/posts.py and so on) and include
them here. Keep this file small.
"""
from __future__ import annotations

from fastapi import Depends, FastAPI, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app import security, settings
from app.guards import NeedsLogin, require_editor_or_admin
from app.publish import CSS
from app.routes import auth, posts

templates = Jinja2Templates(directory=str(settings.TEMPLATES))


def create_app() -> FastAPI:
    app = FastAPI(title="IPHS 400 MP2 CMS")
    app.include_router(auth.router)
    app.include_router(posts.router)

    @app.exception_handler(NeedsLogin)
    def _redirect_to_login(request: Request, exc: NeedsLogin):
        return RedirectResponse("/login", status_code=303)

    @app.get("/admin")
    def admin_home(request: Request, user=Depends(require_editor_or_admin)):
        csrf_token, new_cookie = security.read_or_mint_csrf(request)
        context = {"title": "Admin", "current_user": user, "csrf_token": csrf_token}
        response = templates.TemplateResponse(request, "admin/hello.html", context)
        return security.set_csrf_cookie(response, new_cookie)

    @app.get("/")
    def public_home(request: Request):
        return templates.TemplateResponse(
            request, "public/home.html",
            {"title": settings.SITE_TITLE, "items": []},
        )

    @app.get("/style.css")
    def style_css():
        return Response(CSS, media_type="text/css")

    return app


app = create_app()
