"""T11: every admin link and form action is relative and resolves to a real
route from the page it appears on (ticket #12). check_submission.py rejects
any `href="/` in a template, and a relative link is only right if it's
right at that page's depth -- so resolve each one the way a browser would.
"""
from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

import pytest

from app import content as content_module
from app import db as db_module

BASE = "http://testserver"


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []
        self.forms: list[tuple[str, str]] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("a", "link") and attrs.get("href"):
            self.hrefs.append(attrs["href"])
        if tag == "form" and attrs.get("action"):
            self.forms.append((attrs.get("method", "get").lower(), attrs["action"]))


@pytest.fixture
def seeded_ids():
    conn = db_module.connect()
    try:
        admin_id = conn.execute(
            "SELECT id FROM users WHERE email = 'admin@example.test'"
        ).fetchone()["id"]
    finally:
        conn.close()
    ids = {
        "post_id": content_module.create_content("post", "P", "p", "x", admin_id),
        "page_id": content_module.create_content("page", "Pg", "pg", "x", admin_id),
    }
    # A second save gives each edit screen a Roll back form to check.
    content_module.update_content(ids["post_id"], "post", "P", "p", "y", saved_by=admin_id)
    content_module.update_content(ids["page_id"], "page", "Pg", "pg", "y", saved_by=admin_id)
    # A Scheduled Page: its edit screen adds a Cancel schedule form, and the
    # lists show its badge.
    assert content_module.set_schedule(ids["page_id"], "page", "2999-01-01 09:00:00")
    return ids


ADMIN_PAGES = [
    "/admin", "/admin/content", "/admin/content?status=scheduled",
    "/admin/posts", "/admin/posts/new", "/admin/posts/{post_id}/edit",
    "/admin/pages", "/admin/pages/new", "/admin/pages/{page_id}/edit",
    "/admin/users", "/admin/users/new",
]


def assert_links_resolve(client, page_path: str, html: str) -> None:
    """Every href/action in `html`, as served at `page_path`, is relative and
    resolves to a real route from there."""
    parser = _Links()
    parser.feed(html)
    assert parser.hrefs, f"no links found on {page_path}"

    page_url = BASE + page_path
    for href in parser.hrefs:
        assert not href.startswith("/"), f"{page_path}: root-absolute href {href!r}"
        target = urlsplit(urljoin(page_url, href))
        status = client.get(target.path, params=target.query or None).status_code
        assert status != 404 and status < 500, f"{page_path}: href {href!r} -> {target.path} is {status}"

    for method, action in parser.forms:
        assert not action.startswith("/"), f"{page_path}: root-absolute action {action!r}"
        target = urlsplit(urljoin(page_url, action)).path
        # An empty submission is rejected (422/403) but must reach a real route.
        status = client.request(method.upper(), target).status_code
        assert status not in (404, 405) and status < 500, f"{page_path}: form {action!r} -> {target} is {status}"


@pytest.mark.parametrize("path_template", ADMIN_PAGES)
def test_every_admin_link_is_relative_and_resolves(client_as, seeded_ids, path_template):
    admin = client_as("admin")
    path = path_template.format(**seeded_ids)
    response = admin.get(path)
    assert response.status_code == 200, path
    assert_links_resolve(admin, path, response.text)


def test_login_page_links_are_relative_and_resolve(client):
    assert_links_resolve(client, "/login", client.get("/login").text)


# A failed POST re-renders a page at the deeper POST URL (e.g. a list page at
# /admin/posts/3/delete), so its links need more "../" than the GET page did.
FAILED_POST_PAGES = [
    "/admin/posts/{post_id}/delete", "/admin/pages/{page_id}/publish",
    "/admin/posts/{post_id}/edit", "/admin/users/{post_id}/role",
    "/admin/posts/{post_id}/revisions/1/rollback",
    "/admin/posts/{post_id}/schedule", "/admin/pages/{page_id}/cancel-schedule",
]


@pytest.mark.parametrize("path_template", FAILED_POST_PAGES)
def test_links_on_a_page_rendered_by_a_failed_post_still_resolve(
    client_as, seeded_ids, path_template,
):
    admin = client_as("admin")
    path = path_template.format(**seeded_ids)
    response = admin.post(path, data={"title": "x", "slug": "x", "body_md": "x",
                                      "role": "editor", "csrf_token": "forged"})
    assert response.status_code == 403, path  # rejected, rendered as an error page
    assert_links_resolve(admin, path, response.text)


@pytest.mark.parametrize("path,section", [
    ("/admin", "Dashboard"), ("/admin/content", "All content"), ("/admin/posts", "Posts"),
    ("/admin/posts/new", "Posts"), ("/admin/pages", "Pages"), ("/admin/users/new", "Users"),
])
def test_admin_nav_marks_the_current_section(client_as, path, section):
    html = client_as("admin").get(path).text
    current = re.findall(r'<a [^>]*aria-current="page"[^>]*>([^<]+)</a>', html)
    assert current == [section], f"{path}: current section {current}"
