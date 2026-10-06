"""The editor's live preview, driven in a real browser: it renders as you
type (T03), never runs injected script (T03, rubric D4), and says so plainly
when the session has expired instead of pasting the login page in (T10).
"""
from __future__ import annotations

import pytest

from app import content as content_module
from app import db as db_module
from app.publish import render_site
from tests.conftest import DEMO_USERS, log_in

XSS_BODY = ('<script>window.__xss = 1</script>\n\n'
            '<img src="x" onerror="window.__xss = 2">\n\n**after**')


@pytest.fixture
def editor_page(phone):
    log_in(phone, "editor")
    phone.goto("/admin/posts/new")
    return phone


def test_preview_renders_markdown_as_you_type(editor_page):
    editor_page.fill("#body_md", "Hello **bold** world")
    editor_page.wait_for_selector("#preview strong", timeout=5000)
    assert editor_page.inner_text("#preview strong") == "bold"


def test_script_typed_into_the_editor_never_runs_in_the_preview(editor_page):
    # Browsers never run a <script> inserted via innerHTML, so here only the
    # onerror half can catch a sanitizer gap; the saved-Post test below
    # covers <script> too, because there the preview is rendered server-side.
    editor_page.fill("#body_md", XSS_BODY)
    assert_no_script_ran(editor_page, "#preview")


def assert_no_script_ran(page, scope: str) -> None:
    page.wait_for_selector(f"{scope} strong", timeout=5000)
    # onerror fires after the image fails to load, so wait for that attempt.
    page.wait_for_function(
        f"[...document.querySelectorAll('{scope} img')].every(img => img.complete)",
        timeout=5000)
    assert page.evaluate("typeof window.__xss") == "undefined", page.url


def test_saved_post_with_script_never_runs_in_editor_or_export(phone, tmp_path):
    conn = db_module.connect()
    try:
        author = conn.execute("SELECT id FROM users WHERE email = ?",
                              (DEMO_USERS["admin"]["email"],)).fetchone()["id"]
    finally:
        conn.close()
    post_id = content_module.create_content("post", "Tricky", "tricky", XSS_BODY, author)
    content_module.set_status(post_id, "post", content_module.STATUS_PUBLISHED)

    log_in(phone, "editor")
    phone.goto(f"/admin/posts/{post_id}/edit")
    assert_no_script_ran(phone, "#preview")

    exported = render_site(tmp_path / "site") / "posts" / "tricky.html"
    phone.goto(exported.as_uri())
    assert_no_script_ran(phone, "main")


def test_preview_says_session_expired_instead_of_showing_the_login_page(editor_page):
    editor_page.context.clear_cookies()  # the session ends while the editor is open
    editor_page.fill("#body_md", "Still typing after the session ended")
    editor_page.wait_for_function(
        "document.getElementById('preview').textContent.includes('session may have expired')",
        timeout=5000)
    assert editor_page.locator("#preview input[name=password]").count() == 0
