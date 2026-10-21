"""MP2plus F8: Switchable theme (issue #23). Each test is named after the
acceptance step it checks:

  1. Two themes exist, each one CSS file in its own folder under app/themes/
  2. The admin Settings page selects the theme, and the choice survives a
     server restart
  3. `uv run cms publish` writes the selected theme's CSS as site/style.css,
     so every page's relative stylesheet link still works
  4. Switching back and publishing again restores the first theme's CSS
  5. Both themes show no horizontal overflow at 390 px on the home page and
     one post
  6. The Settings form carries a CSRF token; its POST replayed without the
     token is refused
"""
from __future__ import annotations

import functools
import http.server
import os
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from app import cli, settings
from app import theme as theme_module
from tests.conftest import extract_csrf, log_in
from tests.test_phone_width import assert_fits_phone
from tests.test_phone_width import awkward_content  # noqa: F401 (a fixture)

ROOT = Path(__file__).resolve().parents[1]
THEMES_DIR = ROOT / "app" / "themes"


def _theme_file(name: str) -> bytes:
    return (THEMES_DIR / name / "style.css").read_bytes()


def _theme_options(html: str) -> dict[str, bool]:
    """The Settings page's theme choices: each radio's value, and whether
    it is the checked one."""
    radios = re.findall(r'<input [^>]*name="theme"[^>]*>', html)
    return {re.search(r'value="([^"]*)"', radio).group(1): " checked" in radio
            for radio in radios}


def _choose_theme(admin, name: str):
    """Pick a theme on the Settings page, as an Admin would."""
    token = extract_csrf(admin.get("/admin/settings").text)
    return admin.post("/admin/settings", data={"theme": name, "csrf_token": token},
                      follow_redirects=False)


# Each theme's light --bg, so a browser test can tell which stylesheet loaded.
PAGE_BACKGROUND = {"default": "rgb(245, 246, 250)", "chapter": "rgb(248, 246, 240)"}


def _body_background(page) -> str:
    return page.evaluate("getComputedStyle(document.body).backgroundColor")


# -- Step 1: two themes, each one CSS file in its own folder under app/themes/ --

def test_step1_two_themes_each_one_css_file_in_its_own_folder():
    folders = sorted(path for path in THEMES_DIR.iterdir() if path.is_dir())

    assert [folder.name for folder in folders] == ["chapter", "default"]
    for folder in folders:
        assert [file.name for file in folder.iterdir()] == ["style.css"], folder


def _classes(name: str) -> set[str]:
    """Every class name theme `name`'s stylesheet has a rule for."""
    css = re.sub(r"/\*.*?\*/", "", _theme_file(name).decode("utf-8"), flags=re.DOTALL)
    return set(re.findall(r"\.([A-Za-z_][\w-]*)", css))


def test_step1_each_theme_styles_every_class_the_other_does():
    # The whole admin console follows the theme too, so a class one theme
    # forgets is an unstyled screen. This compares class names only: a
    # layout value changed in one file and not the other still passes, so
    # the step 5 tests below check the layout itself at 390 px.
    assert {"admin-nav", "post-card", "theme-option"} <= _classes("default")
    assert _classes("chapter") == _classes("default")


# -- Step 2: the admin Settings page selects the theme, and the choice
#    survives a server restart --

def test_step2_an_admin_picks_the_theme_on_the_settings_page(client_as):
    admin = client_as("admin")
    assert _theme_options(admin.get("/admin/settings").text) == {
        "default": True, "chapter": False}

    saved = _choose_theme(admin, "chapter")

    assert saved.status_code == 303
    page = admin.get(saved.headers["location"]).text
    assert "Theme saved" in page
    assert _theme_options(page) == {"default": False, "chapter": True}


def test_step2_the_console_and_the_preview_load_the_chosen_theme(client_as):
    admin = client_as("admin")
    assert admin.get("/style.css").content == _theme_file("default")

    _choose_theme(admin, "chapter")

    response = admin.get("/style.css")
    assert response.headers["content-type"].startswith("text/css")
    assert response.content == _theme_file("chapter")


# A server started afresh: a new Python process on the same database, so
# nothing held in the first process's memory can carry the choice over.
RESTARTED_SERVER = """
import sys
from fastapi.testclient import TestClient
from app.main import create_app
sys.stdout.buffer.write(TestClient(create_app()).get("/style.css").content)
"""


def test_step2_the_choice_survives_a_server_restart(client_as):
    _choose_theme(client_as("admin"), "chapter")

    restarted = subprocess.run(
        [sys.executable, "-c", RESTARTED_SERVER], cwd=ROOT, capture_output=True,
        env={**os.environ, "CMS_DATABASE": str(settings.DATABASE_PATH)}, timeout=60,
    )

    assert restarted.returncode == 0, restarted.stderr.decode(errors="replace")
    assert restarted.stdout == _theme_file("chapter")


def test_step2_an_editor_can_neither_open_nor_post_the_settings_page(client_as, client):
    editor = client_as("editor")
    token = extract_csrf(editor.get("/admin").text)

    assert editor.get("/admin/settings").status_code == 403
    refused = editor.post("/admin/settings", data={"theme": "chapter", "csrf_token": token})
    assert refused.status_code == 403
    assert "Only an Admin" in refused.text
    assert client.get("/style.css").content == _theme_file("default")


def test_step2_an_anonymous_visitor_is_sent_to_log_in(client):
    for response in (client.get("/admin/settings", follow_redirects=False),
                     client.post("/admin/settings", data={"theme": "chapter"},
                                 follow_redirects=False)):
        assert response.status_code == 303
        assert response.headers["location"] == "/login"
    assert client.get("/style.css").content == _theme_file("default")


def test_step2_only_admins_see_settings_in_the_nav(client_as):
    assert 'href="admin/settings"' in client_as("admin").get("/admin").text
    assert "admin/settings" not in client_as("editor").get("/admin").text


@pytest.mark.parametrize("name", ["", "nope", "../default", "default/../chapter"])
def test_step2_a_theme_that_is_not_listed_is_refused(client_as, name):
    admin = client_as("admin")

    refused = _choose_theme(admin, name)

    assert refused.status_code == 400
    assert "Pick one of the themes listed" in refused.text
    assert admin.get("/style.css").content == _theme_file("default")


@pytest.mark.parametrize("name", ["default", "chapter"])
def test_step2_the_settings_page_fits_a_390px_phone(client_as, phone, name):
    # In Chromium; skipped without it.
    _choose_theme(client_as("admin"), name)
    log_in(phone, "admin")

    phone.goto("/admin/settings")

    assert _body_background(phone) == PAGE_BACKGROUND[name]
    assert_fits_phone(phone)


# -- Step 3: `cms publish` writes the selected theme's CSS as site/style.css,
#    so every page's relative stylesheet link still works --

def _publish(monkeypatch, tmp_path) -> Path:
    """Run `cms publish` into a site/ of this test's own."""
    site = tmp_path / "site"
    monkeypatch.setattr(settings, "SITE", site)
    assert cli.main(["publish"]) == 0
    return site


def test_step3_publish_writes_the_selected_themes_css_as_site_style_css(
    client_as, monkeypatch, tmp_path,
):
    _choose_theme(client_as("admin"), "chapter")

    site = _publish(monkeypatch, tmp_path)

    assert (site / "style.css").read_bytes() == _theme_file("chapter")


def test_step3_every_exported_page_links_that_stylesheet_relatively(
    client_as, awkward_content, monkeypatch, tmp_path,
):
    _choose_theme(client_as("admin"), "chapter")

    site = _publish(monkeypatch, tmp_path)

    pages = sorted(site.rglob("*.html"))
    assert {page.relative_to(site).as_posix() for page in pages} == {
        "index.html", "search.html", "posts/wide-post.html", "wide-page.html"}
    for page in pages:
        href = re.search(r'<link rel="stylesheet" href="([^"]+)">',
                         page.read_text(encoding="utf-8")).group(1)
        assert not href.startswith("/"), page
        assert (page.parent / href).resolve() == (site / "style.css").resolve(), page


def test_step3_a_chosen_theme_that_is_later_removed_falls_back_to_the_default(
    client_as, monkeypatch, tmp_path,
):
    themes = tmp_path / "themes"
    shutil.copytree(THEMES_DIR, themes)
    monkeypatch.setattr(theme_module, "THEMES_DIR", themes)
    admin = client_as("admin")
    _choose_theme(admin, "chapter")

    shutil.rmtree(themes / "chapter")

    assert admin.get("/style.css").content == _theme_file("default")
    assert (_publish(monkeypatch, tmp_path) / "style.css").read_bytes() == _theme_file("default")
    assert _theme_options(admin.get("/admin/settings").text) == {"default": True}


# -- Step 4: switching back and publishing again restores the first theme's CSS --

def test_step4_switching_back_and_publishing_again_restores_the_first_theme(
    client_as, monkeypatch, tmp_path,
):
    admin = client_as("admin")
    _choose_theme(admin, "chapter")
    site = _publish(monkeypatch, tmp_path)
    assert (site / "style.css").read_bytes() == _theme_file("chapter")

    _choose_theme(admin, "default")
    _publish(monkeypatch, tmp_path)

    assert (site / "style.css").read_bytes() == _theme_file("default")


# -- Step 5: both themes show no horizontal overflow at 390 px on the home
#    page and one post (in Chromium; skipped without it) --

class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture
def exported_site_url(tmp_path):
    """tmp_path/site, where _publish writes the export, served over HTTP as
    `python -m http.server -d site` serves it. Yields its base URL."""
    handler = functools.partial(_QuietHandler, directory=str(tmp_path / "site"))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


@pytest.mark.parametrize("name", ["default", "chapter"])
@pytest.mark.parametrize("path", ["index.html", "posts/wide-post.html"], ids=["home", "post"])
def test_step5_the_published_site_fits_a_390px_phone(
    client_as, awkward_content, phone, exported_site_url, monkeypatch, tmp_path, name, path,
):
    _choose_theme(client_as("admin"), name)
    _publish(monkeypatch, tmp_path)

    phone.goto(f"{exported_site_url}/{path}")

    assert _body_background(phone) == PAGE_BACKGROUND[name]
    assert_fits_phone(phone)


@pytest.mark.parametrize("name", ["default", "chapter"])
@pytest.mark.parametrize("path", ["/", "/posts/wide-post.html"], ids=["home", "post"])
def test_step5_the_dev_server_preview_fits_a_390px_phone(
    client_as, awkward_content, phone, name, path,
):
    _choose_theme(client_as("admin"), name)

    phone.goto(path)

    assert _body_background(phone) == PAGE_BACKGROUND[name]
    assert_fits_phone(phone)


# -- Step 6: the Settings form carries a CSRF token; its POST replayed
#    without the token is refused --

def test_step6_the_settings_form_carries_a_csrf_token(client_as):
    page = client_as("admin").get("/admin/settings").text
    form = re.search(r'<form [^>]*action="[^"]*admin/settings"[^>]*>(.*?)</form>',
                     page, re.DOTALL)

    assert form, "no Settings form on the page"
    assert 'method="post"' in form.group(0)
    assert re.search(r'<input type="hidden" name="csrf_token" value="[^"]+"', form.group(1))


@pytest.mark.parametrize("csrf", [None, "", "forged-token-value"],
                         ids=["absent", "empty", "forged"])
def test_step6_a_settings_post_without_its_csrf_token_is_refused(client_as, csrf):
    admin = client_as("admin")
    admin.get("/admin/settings")  # the page sets the CSRF cookie a real form has
    data = {"theme": "chapter"} if csrf is None else {"theme": "chapter", "csrf_token": csrf}

    refused = admin.post("/admin/settings", data=data, follow_redirects=False)

    assert refused.status_code == 403
    assert "session expired" in refused.text
    assert admin.get("/style.css").content == _theme_file("default")
