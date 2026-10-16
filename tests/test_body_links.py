"""T17: relative links in exported Markdown bodies (ticket #20).

A link written in a body points at another page the way it would on any
website, `[Contact us](/contact-us.html)`. GitHub Pages serves the site from
a subfolder, so the export rewrites that link relative to the file it is
writing: from a Page at the site root it becomes `./contact-us.html`, from a
Post in `posts/` it becomes `../contact-us.html`.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

import pytest

from app import content as content_module
from app import db as db_module
from app.publish import render_site


def _admin_id() -> int:
    conn = db_module.connect()
    try:
        return conn.execute(
            "SELECT id FROM users WHERE email = 'admin@example.test'"
        ).fetchone()["id"]
    finally:
        conn.close()


def _publish(kind: str, slug: str, body_md: str) -> None:
    content_id = content_module.create_content(kind, slug.title(), slug, body_md, _admin_id())
    content_module.set_status(content_id, kind, "published")


def _href(html: str, link_text: str) -> str:
    """The href of the body link whose text is `link_text` (not a nav link)."""
    match = re.search(rf'<a href="([^"]*)"[^>]*>{re.escape(link_text)}</a>', html)
    assert match, f"no link {link_text!r} in the page"
    return match.group(1)


def _img_src(html: str, alt: str) -> str:
    tag = re.search(rf'<img [^>]*alt="{re.escape(alt)}"[^>]*>', html)
    assert tag, f"no image {alt!r} in the page"
    return re.search(r'src="([^"]*)"', tag.group(0)).group(1)


def _read(path) -> str:
    return path.read_text(encoding="utf-8")


def test_a_root_absolute_link_and_image_in_a_page_body_are_exported_relative(tmp_path):
    _publish("page", "about", "[Contact us](/contact-us.html)\n\n![Club logo](/logo.png)")

    html = _read(render_site(tmp_path / "site") / "about.html")
    assert _href(html, "Contact us") == "./contact-us.html"
    assert _img_src(html, "Club logo") == "./logo.png"


def test_a_root_absolute_link_and_image_in_a_post_body_climb_out_of_posts(tmp_path):
    _publish("post", "hour-of-code", "[Contact us](/contact-us.html)\n\n![Club logo](/logo.png)")

    html = _read(render_site(tmp_path / "site") / "posts" / "hour-of-code.html")
    assert _href(html, "Contact us") == "../contact-us.html"
    assert _img_src(html, "Club logo") == "../logo.png"


@pytest.mark.parametrize("url, from_page, from_post", [
    ("/", "./index.html", "../index.html"),
    ("/#join", "./index.html#join", "../index.html#join"),
    ("/?ref=nav", "./index.html?ref=nav", "../index.html?ref=nav"),
])
def test_a_link_to_the_site_root_points_at_the_home_page(tmp_path, url, from_page, from_post):
    _publish("page", "about", f"[Back home]({url})")
    _publish("post", "news", f"[Back home]({url})")

    out = render_site(tmp_path / "site")
    assert _href(_read(out / "about.html"), "Back home") == from_page
    assert _href(_read(out / "posts" / "news.html"), "Back home") == from_post


def test_a_protocol_relative_link_is_exported_as_https(tmp_path):
    _publish("post", "news", "[Docs](//example.com/guide.html)")

    html = _read(render_site(tmp_path / "site") / "posts" / "news.html")
    assert _href(html, "Docs") == "https://example.com/guide.html"


@pytest.mark.parametrize("url", [
    "https://example.com/guide.html",
    "#eligibility",
    "mailto:advisor@example.test",
    "coursework.html",
    "../index.html",
])
def test_other_links_are_exported_exactly_as_written(tmp_path, url):
    _publish("post", "news", f"[Other]({url})")

    html = _read(render_site(tmp_path / "site") / "posts" / "news.html")
    assert _href(html, "Other") == url


@pytest.mark.parametrize("body", [
    "[Trick](/javascript:alert(1))",
    '<a href="/JaVaScRiPt:alert(1)">Trick</a>',
    '<a href="/data:text/html,hi">Trick</a>',
    '<a href="/\tjavascript:alert(1)">Trick</a>',
    '<a href=" /javascript:alert(1)">Trick</a>',
])
def test_a_root_link_on_a_page_never_becomes_a_script_link(tmp_path, body):
    """Dropping only the "/" from "/javascript:..." would leave a live
    javascript: link, because nh3 checks schemes before the rewrite runs."""
    _publish("page", "about", body)

    href = _href(_read(render_site(tmp_path / "site") / "about.html"), "Trick")
    assert href.startswith("./"), href
    assert urlsplit(urljoin("https://example.github.io/site/about.html", href)).scheme == "https"


@pytest.mark.parametrize("url, exported", [
    (" /contact-us.html", "./contact-us.html"),
    ("/\tcontact-us.html", "./contact-us.html"),
    ("/\\example.com/guide.html", "https://example.com/guide.html"),
])
def test_links_are_read_the_way_a_browser_reads_them(tmp_path, url, exported):
    """A browser trims spaces, drops tabs, and reads "\\" as "/", so " /x"
    is root-absolute and "/\\host" is protocol-relative."""
    _publish("page", "about", f'<a href="{url}">Odd</a>')

    assert _href(_read(render_site(tmp_path / "site") / "about.html"), "Odd") == exported


def test_no_root_absolute_href_or_src_survives_anywhere_in_the_export(tmp_path):
    bodies = (
        "[Contact us](/contact-us.html) · [Home](/) · [Docs](//example.com/x)\n\n"
        "![Logo](/logo.png)\n\n"
        '<a href="/raw-html.html">raw HTML link</a> <img src="/raw.png" alt="raw"> '
        '<a href=" /padded.html">padded</a> <a href="/\\example.com">backslash</a>'
    )
    _publish("page", "about", bodies)
    _publish("post", "news", bodies)

    out = render_site(tmp_path / "site")
    for path in out.rglob("*.html"):
        html = _read(path)
        assert 'href="/' not in html, f"{path.name} still has a root-absolute href"
        assert 'src="/' not in html, f"{path.name} still has a root-absolute src"
        assert not re.search(r'(href|src)="\s', html), f"{path.name} has a padded link"


def test_the_dev_servers_public_pages_rewrite_links_the_same_way(client):
    _publish("page", "contact-us", "Email the advisor.")
    _publish("post", "hour-of-code", "[Contact us](/contact-us.html)")

    page_url = "http://testserver/posts/hour-of-code.html"
    href = _href(client.get(page_url).text, "Contact us")
    assert href == "../contact-us.html"
    assert client.get(urlsplit(urljoin(page_url, href)).path).status_code == 200


def test_the_admin_preview_keeps_links_as_written(client_as):
    editor = client_as("editor")
    live = editor.post("/admin/posts/preview",
                       data={"body_md": "[Contact us](/contact-us.html)"})
    assert _href(live.text, "Contact us") == "/contact-us.html"

    post_id = content_module.create_content(
        "post", "Draft", "draft", "[Contact us](/contact-us.html)", _admin_id())
    form = editor.get(f"/admin/posts/{post_id}/edit")
    assert _href(form.text, "Contact us") == "/contact-us.html"
