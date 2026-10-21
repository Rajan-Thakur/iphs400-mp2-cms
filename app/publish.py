"""Render the public site into site/ as plain HTML.

T00 publishes a placeholder home page. As you build content types, extend
render_site() to write one file per published item. Two rules the rubric checks:

  1. Only PUBLISHED content is written here. A draft that reaches site/ is a bug.
  2. Every href and src is RELATIVE ("style.css", "posts/x.html"), never
     root-absolute ("/style.css"), because Pages serves this from a subfolder.
     That includes links written in a body: render_markdown(..., to_root=...)
     rewrites "/contact-us.html" and "media/logo.png" for the file it lands in.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app import content as content_module
from app import settings
from app import theme as theme_module
from app.mdrender import render_markdown, render_text

# search.html's one script, which searches site/search-index.json.
SEARCH_JS = Path(__file__).with_name("search.js").read_text(encoding="utf-8")

# The most characters of a body that search.html shows under a result's title.
EXCERPT_LENGTH = 160


def environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(settings.TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )


def nav_items(prefix: str = "") -> list[dict[str, str]]:
    """Published Pages, as relative (title, href) links for the public
    site's nav. `prefix` relocates the link for a page nested one
    directory deep (e.g. "../" from site/posts/*.html) — a draft Page
    never appears here."""
    return [{"title": page["title"], "href": f"{prefix}{page['slug']}.html"}
            for page in _exportable_pages()]


def _exportable_pages() -> list:
    # The editor already refuses reserved slugs; this also covers rows saved
    # before that check existed, so a Page can never overwrite site/index.html.
    return [page for page in content_module.list_published("page")
            if not content_module.reserved_slug_reason("page", page["slug"])]


def _date(item) -> str:
    """The calendar day an item was created, e.g. "2026-10-07"."""
    return item["created_at"][:10]


def home_html() -> str:
    """The home page (feed of published Posts), as written to site/index.html."""
    posts = content_module.list_published("post")
    return environment().get_template("public/home.html").render(
        title=settings.SITE_TITLE, items=[
            {"title": post["title"], "href": f"posts/{post['slug']}.html",
             "date": _date(post)} for post in posts
        ],
        css_path="style.css", home_path="index.html", nav_items=nav_items(),
    )


def search_html() -> str:
    """The search page, as written to site/search.html; its script is
    site/search.js."""
    return environment().get_template("public/search.html").render(
        title="Search", site_title=settings.SITE_TITLE,
        css_path="style.css", home_path="index.html", nav_items=nav_items(),
    )


def search_index_json() -> str:
    """site/search-index.json: the title, URL and a plain-text excerpt of
    every published Post and Page, for search.html's script to search. Each
    URL is relative to the site root, where search.html is."""
    items = [(post, f"posts/{post['slug']}.html")
             for post in content_module.list_published("post")]
    items += [(page, f"{page['slug']}.html") for page in _exportable_pages()]
    return json.dumps([
        {"title": item["title"], "url": url, "excerpt": _excerpt(item["body_md"])}
        for item, url in items
    ], ensure_ascii=False, indent=1)


def _excerpt(body_md: str) -> str:
    """The start of a body as plain text, EXCERPT_LENGTH characters or fewer
    with the "…" that ends it when anything was cut. The cut falls at a word
    break, unless the text has none to fall at."""
    text = render_text(body_md)
    if len(text) <= EXCERPT_LENGTH:
        return text
    head = text[:EXCERPT_LENGTH]
    cut = head.rsplit(" ", 1)[0] if " " in head else head[:-1]
    return (cut.rstrip(" .,;:") or cut) + "…"


def post_html(post) -> str:
    """A published Post, as written to site/posts/<slug>.html — one directory
    deep, so every shared link climbs a level."""
    return _detail_html("public/post.html", "post", post, prefix="../")


def page_html(page) -> str:
    """A published Page, as written to site/<slug>.html."""
    return _detail_html("public/page.html", "page", page, prefix="")


def _detail_html(template_name: str, item_key: str, item, *, prefix: str) -> str:
    return environment().get_template(template_name).render(
        title=item["title"], site_title=settings.SITE_TITLE,
        **{item_key: item}, date=_date(item),
        body_html=render_markdown(item["body_md"], to_root=prefix),
        css_path=f"{prefix}style.css", home_path=f"{prefix}index.html",
        nav_items=nav_items(prefix=prefix),
    )


def _write(path: Path, text: str) -> None:
    # Explicit UTF-8: the pages declare <meta charset="utf-8">, and the
    # platform default (cp1252 on Windows) can't encode an emoji at all.
    path.write_text(text, encoding="utf-8")


def render_site(out: Path | None = None) -> Path:
    out = out or settings.SITE
    # The selected Theme's file, byte for byte, under the one name every
    # page links: switching themes changes the file, never the links. Read
    # before site/ is cleared, so a failure here leaves the last export whole.
    css = theme_module.stylesheet().read_bytes()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / "style.css").write_bytes(css)
    _write(out / "index.html", home_html())
    _write(out / "search.html", search_html())
    _write(out / "search.js", SEARCH_JS)
    _write(out / "search-index.json", search_index_json())

    posts_dir = out / "posts"
    posts_dir.mkdir()
    for post in content_module.list_published("post"):
        _write(posts_dir / f"{post['slug']}.html", post_html(post))
    for page in _exportable_pages():
        _write(out / f"{page['slug']}.html", page_html(page))

    # Every file in media/ is meant to be public; Posts show them through
    # their Media library snippets.
    if settings.MEDIA.is_dir():
        shutil.copytree(settings.MEDIA, out / "media")

    return out
