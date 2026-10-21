"""MP2plus F5: site search (issue #22).

`cms publish` writes search-index.json (the title, relative URL and a short
excerpt of each published Post and Page) and search.html, which searches it
with one short script; the home page links to search.html. The dev server
serves the same files at the same paths, through the same app.publish code,
so most tests read them over HTTP; two run `cms publish` itself. Each test is
named after the acceptance step on #22 it checks.
"""
from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import pytest

from app import cli, settings
from app import content as content_module
from app import db as db_module
from tests.conftest import extract_csrf

BASE = "http://testserver"


def _admin_id() -> int:
    conn = db_module.connect()
    try:
        return conn.execute(
            "SELECT id FROM users WHERE email = 'admin@example.test'"
        ).fetchone()["id"]
    finally:
        conn.close()


def _seed(kind: str, title: str, slug: str, body_md: str, status: str = "published") -> int:
    content_id = content_module.create_content(kind, title, slug, body_md, _admin_id())
    if status == "published":
        content_module.set_status(content_id, kind, "published")
    return content_id


# -- Step 1: the index has the title, relative URL and a short excerpt of each
#    published Post and Page --

def test_step1_the_index_lists_each_published_post_and_page(client):
    _seed("post", "Robotics club kickoff", "robotics-kickoff", "Meet us in room 204.")
    _seed("page", "About us", "about-us", "We promote computer science.")

    response = client.get("/search-index.json")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == [
        {"title": "Robotics club kickoff", "url": "posts/robotics-kickoff.html",
         "excerpt": "Meet us in room 204."},
        {"title": "About us", "url": "about-us.html",
         "excerpt": "We promote computer science."},
    ]


def test_step1_the_excerpt_is_short_plain_text(client):
    body = ("# Welcome\n\nJoin **CS Honor Society** & meet [our officers](/about-us.html)."
            "\n\n<script>alert(1)</script>\n\n" + "lorem " * 80)
    _seed("post", "Welcome", "welcome", body)

    excerpt = client.get("/search-index.json").json()[0]["excerpt"]

    assert excerpt.startswith("Welcome Join CS Honor Society & meet our officers. lorem lorem")
    assert "<" not in excerpt and "alert" not in excerpt and "&amp;" not in excerpt
    assert len(excerpt) <= 160 and excerpt.endswith("lorem…"), excerpt


@pytest.mark.parametrize("body", ["lorem " * 80, "x" * 300, "... " * 100, "長" * 300],
                         ids=["words", "one-long-word", "punctuation", "no-spaces"])
def test_step1_a_long_excerpt_is_160_characters_or_fewer_with_an_ellipsis(client, body):
    _seed("post", "Long post", "long-post", body)

    excerpt = client.get("/search-index.json").json()[0]["excerpt"]

    assert 100 < len(excerpt) <= 160 and excerpt.endswith("…"), excerpt


def test_step1_the_excerpt_keeps_words_from_separate_blocks_apart(client):
    _seed("post", "Blocks", "blocks",
          "<div>alpha</div><div>beta</div>\n\n<table><tr><td>c1</td><td>c2</td></tr></table>"
          "\n\nline one<br>line two")

    excerpt = client.get("/search-index.json").json()[0]["excerpt"]

    assert excerpt == "alpha beta c1 c2 line one line two"


def _publish(monkeypatch, tmp_path) -> Path:
    """Run `cms publish` into a temporary site/ and return it."""
    site = tmp_path / "site"
    monkeypatch.setattr(settings, "SITE", site)
    assert cli.main(["publish"]) == 0
    return site


def test_step1_cms_publish_writes_the_index_and_search_page_the_dev_server_serves(
    client, monkeypatch, tmp_path,
):
    _seed("post", "Robotics club kickoff", "robotics-kickoff", "Meet us in room 204.")
    _seed("page", "About us", "about-us", "We promote computer science.")

    site = _publish(monkeypatch, tmp_path)

    index = json.loads((site / "search-index.json").read_text(encoding="utf-8"))
    assert [item["title"] for item in index] == ["Robotics club kickoff", "About us"]
    assert index == client.get("/search-index.json").json()
    for name in ("search.html", "search.js"):
        assert (site / name).read_text(encoding="utf-8") == client.get(f"/{name}").text


# -- Step 2: Drafts are absent from the index --

def test_step2_drafts_are_absent_from_the_index(client):
    _seed("post", "Live post", "live-post", "Public words.")
    _seed("post", "Secret draft post", "secret-post", "Hidden words.", status="draft")
    _seed("page", "Secret draft page", "secret-page", "Hidden words.", status="draft")
    scheduled = _seed("post", "Secret scheduled post", "secret-scheduled", "Hidden words.",
                      status="draft")
    content_module.set_schedule(scheduled, "post", "2099-01-01 00:00:00")
    unpublished = _seed("page", "Secret unpublished page", "secret-unpublished", "Hidden words.")
    content_module.set_status(unpublished, "page", "draft")

    response = client.get("/search-index.json")

    assert [item["title"] for item in response.json()] == ["Live post"]
    assert "secret" not in response.text.lower() and "hidden" not in response.text.lower()


def test_step2_cms_publish_leaves_drafts_out_of_every_file(monkeypatch, tmp_path):
    # Words no template, stylesheet or script contains, unlike "hidden".
    _seed("post", "Live post", "live-post", "Public words.")
    _seed("post", "Quetzal draft post", "quetzal-post", "Ocelot words.", status="draft")
    _seed("page", "Quetzal draft page", "quetzal-page", "Ocelot words.", status="draft")

    site = _publish(monkeypatch, tmp_path)

    assert "Live post" in (site / "search-index.json").read_text(encoding="utf-8")
    for path in site.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8").lower()
            assert "quetzal" not in text and "ocelot" not in text, path


# -- Step 3: search.html loads one plain JavaScript file of 60 lines or fewer,
#    with no external dependency and relative paths only --

def _is_relative(url: str) -> bool:
    """True for a URL that resolves against the page it is on: no scheme,
    no host, and no leading slash."""
    parts = urlsplit(url)
    return not (parts.scheme or parts.netloc or url.startswith(("/", "\\")))


def _scripts(html: str) -> list[tuple[str, str]]:
    """(attributes, inline code) of every <script> element in `html`."""
    return re.findall(r"<script\b([^>]*)>(.*?)</script\s*>", html, re.S | re.I)


def test_step3_search_html_loads_one_local_script_of_at_most_60_lines(client):
    page = client.get("/search.html")
    assert page.status_code == 200

    [(attributes, inline)] = _scripts(page.text)
    assert inline.strip() == ""
    src = unescape(re.search(r'\bsrc="([^"]*)"', attributes).group(1))
    assert _is_relative(src), src
    script = client.get(urlsplit(urljoin(BASE + "/search.html", src)).path)
    assert script.status_code == 200
    assert "javascript" in script.headers["content-type"]
    assert len(script.text.splitlines()) <= 60


def test_step3_search_html_and_its_script_use_only_relative_urls(client):
    _seed("post", "Robotics club kickoff", "robotics-kickoff", "Meet us in room 204.")
    _seed("page", "About us", "about-us", "We promote computer science.")
    page = client.get("/search.html").text

    urls = [unescape(url) for url in re.findall(r'\b(?:href|src)="([^"]*)"', page)]
    assert urls and all(_is_relative(url) for url in urls), urls
    [(attributes, _)] = _scripts(page)
    src = unescape(re.search(r'\bsrc="([^"]*)"', attributes).group(1))
    script = client.get(urlsplit(urljoin(BASE + "/search.html", src)).path).text
    # No library pulled in, and no string the script could fetch from the root
    # or another host ("/search-index.json" fails on a Pages subfolder).
    assert not re.search(r"\b(import|require)\s*\(|\bimport\s", script)
    assert "://" not in script
    assert not re.search(r"""["'`]/""", script), "a string in the script starts with /"
    assert all(_is_relative(item["url"]) for item in client.get("/search-index.json").json())


# A Page is exported to site/<slug>.html, so a Page with slug "search" would
# overwrite site/search.html and its script with the Page's own text.

def test_step3_a_page_cannot_take_the_search_slug_and_replace_search_html(client_as):
    editor = client_as("editor")
    response = editor.post("/admin/pages/new", data={
        "title": "Search", "slug": "search", "body_md": "x",
        "csrf_token": extract_csrf(editor.get("/admin/pages/new").text),
    })

    assert response.status_code == 200
    assert "reserved" in response.text.lower()
    assert content_module.list_content("page") == []


def test_step3_an_older_page_with_the_search_slug_cannot_replace_search_html(
    client, monkeypatch, tmp_path,
):
    # Saved before "search" was reserved, which the editor no longer allows.
    _seed("page", "Old search page", "search", "Saved before the slug was reserved.")

    page = client.get("/search.html").text
    site = _publish(monkeypatch, tmp_path)

    assert "Old search page" not in page and len(_scripts(page)) == 1
    assert (site / "search.html").read_text(encoding="utf-8") == page
    assert client.get("/search-index.json").json() == []


# -- Step 5: the published home page links to search.html with a relative path --

def test_step5_the_home_page_links_to_search_html_with_a_relative_path(client):
    home = client.get("/index.html").text

    hrefs = [unescape(href) for href in re.findall(r'<a\b[^>]*\bhref="([^"]*)"', home)]
    search_links = [href for href in hrefs
                    if urlsplit(urljoin(BASE + "/index.html", href)).path == "/search.html"]
    assert search_links, hrefs
    assert all(_is_relative(href) for href in search_links), search_links
    assert client.get("/search.html").status_code == 200
