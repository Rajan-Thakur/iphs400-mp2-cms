"""No page scrolls sideways on a 390px phone (T01, T03, T05, T08 acceptance
criteria; rubric F3). Measured in a real browser: the page fits when the
document is no wider than the viewport. The content is deliberately awkward --
a long unbroken title, a long URL, a wide code block -- because that's what
real posts contain and what pushes a narrow layout sideways.
"""
from __future__ import annotations

import pytest

from app import content as content_module
from app import db as db_module
from tests.conftest import log_in

LONG_WORD = "Supercalifragilisticexpialidocious-and-then-some-more-words-joined"
WIDE_BODY = (
    "See https://example.org/a/very/long/path/that/never/breaks/on/its/own/at/all.html\n\n"
    "```\n" + "print('a line of code far wider than any phone screen') " * 3 + "\n```\n\n"
    "| Column one | Column two | Column three | Column four | Column five |\n"
    "|---|---|---|---|---|\n"
    "| some cell text | some cell text | some cell text | some cell text | some cell text |\n"
)


def _admin_id() -> int:
    conn = db_module.connect()
    try:
        return conn.execute(
            "SELECT id FROM users WHERE email = 'admin@example.test'").fetchone()["id"]
    finally:
        conn.close()


@pytest.fixture
def awkward_content():
    """A published Post and Page whose title and body are hard to fit, each
    saved twice so its edit screen lists a revision with a Roll back button."""
    author = _admin_id()
    ids = {}
    for kind in ("post", "page"):
        ids[kind] = content_module.create_content(
            kind, f"{kind.title()} {LONG_WORD}", f"wide-{kind}", WIDE_BODY, author)
        content_module.update_content(
            ids[kind], kind, f"{kind.title()} {LONG_WORD}", f"wide-{kind}",
            WIDE_BODY + "\nMore.", saved_by=author)
        content_module.set_status(ids[kind], kind, content_module.STATUS_PUBLISHED)
    return ids


def assert_fits_phone(page) -> None:
    overflow = page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth")
    assert overflow <= 0, f"{page.url} is {overflow}px wider than a 390px phone"


@pytest.mark.parametrize("path", ["/", "/posts/wide-post.html", "/wide-page.html"])
def test_public_pages_fit_a_phone(phone, awkward_content, path):
    phone.goto(path)
    assert_fits_phone(phone)


def test_login_page_fits_a_phone(phone):
    phone.goto("/login")
    assert_fits_phone(phone)


def test_login_page_with_its_error_message_fits_a_phone(phone):
    phone.goto("/login")
    phone.fill("input[name=email]", "admin@example.test")
    phone.fill("input[name=password]", "not-the-password")
    phone.click("button[type=submit]")
    phone.wait_for_selector(".error", timeout=5000)
    assert_fits_phone(phone)


ADMIN_SCREENS = [
    "/admin", "/admin/content", "/admin/content?status=published&type=post",
    "/admin/posts", "/admin/posts/new", "/admin/posts/{post}/edit",
    "/admin/pages", "/admin/pages/new", "/admin/pages/{page}/edit",
    "/admin/users", "/admin/users/new",
]


@pytest.mark.parametrize("path", ADMIN_SCREENS)
def test_admin_screens_fit_a_phone(phone, awkward_content, path):
    log_in(phone, "admin")
    phone.goto(path.format(**awkward_content))
    assert_fits_phone(phone)


def test_editor_denied_page_fits_a_phone(phone):
    log_in(phone, "editor")
    response = phone.goto("/admin/users")
    assert response.status == 403
    assert_fits_phone(phone)
