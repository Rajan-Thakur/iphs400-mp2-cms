"""The FastAPI application.

T00 (already done): the admin console answers at /admin and the public site
answers at /. That is the whole skeleton — it exists so you can prove the stack
runs before you build anything on it.

Add your routes in their own modules (app/routes/posts.py and so on) and include
them here. Keep this file small.
"""
from __future__ import annotations

from fastapi import FastAPI, Request, Response
from fastapi.templating import Jinja2Templates

from app import security, settings
from app.publish import CSS
from app.routes import auth
from app.routes.auth import current_user

templates = Jinja2Templates(directory=str(settings.TEMPLATES))


def create_app() -> FastAPI:
    app = FastAPI(title="IPHS 400 MP2 CMS")
    app.include_router(auth.router)

    @app.get("/admin")
    def admin_home(request: Request):
        user = current_user(request)
        csrf_token, new_cookie = (None, None)
        if user is not None:
            csrf_token, new_cookie = security.read_or_mint_csrf(request)
        context = {"title": "Admin", "current_user": user, "csrf_token": csrf_token}
        response = templates.TemplateResponse(request, "admin/hello.html", context)
        if new_cookie is not None:
            response.set_cookie(security.CSRF_COOKIE, new_cookie, httponly=True, samesite="lax")
        return response

    @app.get("/")
    def public_home(request: Request):
        return templates.TemplateResponse(
            request, "public/home.html",
            {"title": settings.SITE_TITLE, "items": []},
        )

    @app.get("/style.css")
    def style_css():
        return Response(CSS, media_type="text/css")

    # Your ticket work plugs in here, e.g.
    #   from app.routes import posts
    #   app.include_router(posts.router)
    return app


app = create_app()
