"""The one Jinja2Templates instance the admin console renders with."""
from __future__ import annotations

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app import settings


def _relative_root(request: Request) -> dict[str, str]:
    """`to_root`: the "../" steps from the current URL back to the server root,
    so admin links are relative like the published site's, e.g.
    /admin -> "", /admin/posts -> "../", /admin/posts/3/edit -> "../../../"."""
    return {"to_root": "../" * max(request.url.path.count("/") - 1, 0)}


templates = Jinja2Templates(
    directory=str(settings.TEMPLATES), context_processors=[_relative_root],
)
