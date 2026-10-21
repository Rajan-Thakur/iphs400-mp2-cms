"""The one Jinja2Templates instance the admin console renders with."""
from __future__ import annotations

import re

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app import settings


TO_ROOT_RE = re.compile(r"(?:\.\./)*")


def to_root_from(path: str) -> str:
    """`to_root`: the "../" steps from URL `path` back to the server root, so
    admin links are relative like the published site's, e.g.
    /admin -> "", /admin/posts -> "../", /admin/posts/3/edit -> "../../../"."""
    return "../" * max(path.count("/") - 1, 0)


def is_to_root(value: str) -> bool:
    """Whether `value` has the shape to_root_from() gives: only "../" steps.
    A value sent back by a page is checked with this before it is used."""
    return TO_ROOT_RE.fullmatch(value) is not None


def _relative_root(request: Request) -> dict[str, str]:
    """`to_root` for the current URL, in every admin template."""
    return {"to_root": to_root_from(request.url.path)}


def utc_time(stamp: str) -> str:
    """A stored UTC timestamp ("2026-10-08 09:30:00") as shown in the admin
    console: to the minute, marked UTC, e.g. "2026-10-08 09:30 UTC"."""
    return f"{stamp[:16]} UTC"


templates = Jinja2Templates(
    directory=str(settings.TEMPLATES), context_processors=[_relative_root],
)
templates.env.filters["utc_time"] = utc_time
