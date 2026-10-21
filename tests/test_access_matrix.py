"""S1: direct-URL access matrix (MP2plus, checklist #10).

Access control has to live in code, not in which links the nav happens to
show. So this file asks every admin-only route, by its URL, whether an
Editor and an anonymous visitor are kept out.

The route list is generated, never typed: it is every route of create_app()
whose dependencies include one made by `guards.admin_only()`. A new
admin-only route written that way is in the matrix with no edit here. A
route that forgets the marker is caught too: every /admin route must carry
either `admin_only()` or `require_editor_or_admin`, or a test below fails.

Path parameters are filled from real rows the `seeded_ids` fixture creates,
so each request names an item that exists, as a real visitor's would.
"""
from __future__ import annotations

import re

import pytest
from fastapi.routing import APIRoute

from app import content as content_module
from app import db as db_module
from app.guards import require_editor_or_admin
from app.main import create_app

try:
    from fastapi.routing import iter_route_contexts
except ImportError:  # FastAPI < 0.141 copied included routes into app.routes
    def iter_route_contexts(routes):
        return iter(routes)


def _depends_on(dependant, is_guard) -> bool:
    """True if any dependency in this tree passes `is_guard`. Walks
    sub-dependencies too, so a guard nested one level down still counts."""
    return any(is_guard(dep.call) or _depends_on(dep, is_guard)
               for dep in dependant.dependencies)


def _is_admin_only(call) -> bool:
    return getattr(call, "admin_only", False)


def http_routes(app) -> list[tuple[str, set[str], object]]:
    """(path template, methods, dependant) for every HTTP route in `app`.

    Since FastAPI 0.141, `app.routes` keeps each include_router() as one
    entry instead of copying its routes in, so the walk goes through
    `iter_route_contexts` (what FastAPI's own OpenAPI generation uses). Each
    context carries the route's full path and its effective dependencies.
    """
    return [
        (context.path, context.methods, context.dependant)
        for context in iter_route_contexts(app.routes)
        # Older FastAPI yields the routes themselves, with no original_route.
        if isinstance(getattr(context, "original_route", context), APIRoute)
    ]


def admin_only_routes(app) -> list[tuple[str, str]]:
    """(method, path template) for every admin-only route in `app`."""
    return sorted(
        (method, path)
        for path, methods, dependant in http_routes(app)
        if _depends_on(dependant, _is_admin_only)
        for method in methods
    )


ADMIN_ONLY_ROUTES = admin_only_routes(create_app())
ROUTE_IDS = [f"{method} {path}" for method, path in ADMIN_ONLY_ROUTES]


@pytest.fixture
def seeded_ids():
    conn = db_module.connect()
    try:
        admin_id = conn.execute(
            "SELECT id FROM users WHERE email = 'admin@example.test'"
        ).fetchone()["id"]
        editor_id = conn.execute(
            "SELECT id FROM users WHERE email = 'editor@example.test'"
        ).fetchone()["id"]
    finally:
        conn.close()
    return {
        "post": content_module.create_content("post", "Matrix Post", "matrix-post", "x", admin_id),
        "page": content_module.create_content("page", "Matrix Page", "matrix-page", "x", admin_id),
        "user": editor_id,
    }


def fill_path(path: str, ids: dict[str, int]) -> str:
    """Replace each {param} with a seeded id: the Editor's id for a user
    route, the seeded Page's id under /admin/pages, and the seeded Post's
    id for anything else (every create and edit records Revision 1, so a
    {version} of 1 is real too)."""
    def seeded(match: re.Match) -> str:
        name = match.group(1)
        if name == "user_id":
            return str(ids["user"])
        if name == "version":
            return "1"
        return str(ids["page"] if path.startswith("/admin/pages/") else ids["post"])

    return re.sub(r"\{(\w+)(?::\w+)?\}", seeded, path)


# -- the generated list is real: not empty, and missing none we know of --

# Not the source of the matrix (that is the router walk above), only a floor
# under it: if a known admin-only route lost its marker, the walk would
# silently skip it, and this is what notices.
KNOWN_ADMIN_ONLY_ROUTES = [
    ("GET", "/admin/users"),
    ("GET", "/admin/users/new"),
    ("POST", "/admin/users/new"),
    ("POST", "/admin/users/{user_id}/role"),
    ("POST", "/admin/users/{user_id}/deactivate"),
    ("POST", "/admin/posts/{item_id}/publish"),
    ("POST", "/admin/posts/{item_id}/unpublish"),
    ("POST", "/admin/posts/{item_id}/schedule"),
    ("POST", "/admin/posts/{item_id}/cancel-schedule"),
    ("POST", "/admin/pages/{item_id}/publish"),
    ("POST", "/admin/pages/{item_id}/unpublish"),
    ("POST", "/admin/pages/{item_id}/schedule"),
    ("POST", "/admin/pages/{item_id}/cancel-schedule"),
    ("GET", "/admin/settings"),
    ("POST", "/admin/settings"),
]


@pytest.mark.parametrize("method,path", KNOWN_ADMIN_ONLY_ROUTES,
                         ids=[f"{m} {p}" for m, p in KNOWN_ADMIN_ONLY_ROUTES])
def test_every_known_admin_only_route_is_in_the_generated_list(method, path):
    assert (method, path) in ADMIN_ONLY_ROUTES


def test_editor_routes_are_not_in_the_generated_list():
    # The walk must tell the two guards apart, or the matrix would claim an
    # Editor is locked out of routes they are meant to use.
    assert ("GET", "/admin") not in ADMIN_ONLY_ROUTES
    assert ("POST", "/admin/posts/{item_id}/edit") not in ADMIN_ONLY_ROUTES


def test_every_admin_route_is_marked_admin_only_or_editor_or_admin():
    # The matrix only sees marked routes. This catches the rest: an /admin
    # route with no guard, or one that calls require_admin directly and so
    # carries no marker the walk can find.
    unclassified = sorted(
        path for path, _, dependant in http_routes(create_app())
        if path.startswith("/admin")
        and not _depends_on(dependant, _is_admin_only)
        and not _depends_on(dependant, lambda call: call is require_editor_or_admin)
    )
    assert unclassified == []


# -- the matrix: every admin-only route, every method --

@pytest.mark.parametrize("method,path", ADMIN_ONLY_ROUTES, ids=ROUTE_IDS)
def test_editor_is_kept_out_of_every_admin_only_route(client_as, seeded_ids, method, path):
    response = client_as("editor").request(
        method, fill_path(path, seeded_ids), follow_redirects=False,
    )
    # Strictly 403, never "or a redirect": these routes redirect after doing
    # the work (Post/Redirect/Get), and a redirect to /login would mean the
    # Editor's session was not recognised, so the role check never ran.
    assert response.status_code == 403
    assert "Access denied" in response.text


@pytest.mark.parametrize("method,path", ADMIN_ONLY_ROUTES, ids=ROUTE_IDS)
def test_anonymous_is_redirected_to_login_from_every_admin_only_route(
    client, seeded_ids, method, path,
):
    response = client.request(method, fill_path(path, seeded_ids), follow_redirects=False)
    assert response.is_redirect
    assert response.headers["location"] == "/login"
