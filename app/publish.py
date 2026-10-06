"""Render the public site into site/ as plain HTML.

T00 publishes a placeholder home page. As you build content types, extend
render_site() to write one file per published item. Two rules the rubric checks:

  1. Only PUBLISHED content is written here. A draft that reaches site/ is a bug.
  2. Every href and src is RELATIVE ("style.css", "posts/x.html"), never
     root-absolute ("/style.css"), because Pages serves this from a subfolder.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app import content as content_module
from app import settings
from app.mdrender import render_markdown

CSS = """/* Minimal starter styles — make them yours. */
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { font: 16px/1.6 system-ui, sans-serif; margin: 0 auto; max-width: 42rem; padding: 1rem;
  overflow-wrap: anywhere; }
/* Wide Markdown (code, tables, images) scrolls inside itself, not the page. */
pre, table { display: block; max-width: 100%; overflow-x: auto; }
td, th { overflow-wrap: normal; }
img { max-width: 100%; height: auto; }
header a { font-weight: 700; text-decoration: none; }
main { margin-block: 2rem; }
input, button, select, textarea { max-width: 100%; font: inherit; }
form.login-form, form.admin-nav__logout { display: flex; flex-direction: column; gap: 0.5rem; max-width: 100%; }
form.admin-nav__logout { display: inline; }
.admin-nav { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center; }
.error { color: #b00020; }
.success { color: #146c2e; }
textarea { width: 100%; }
.content-form label { display: block; margin-block: 0.75rem; }
.content-list { list-style: none; padding: 0; }
.content-list__item { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center;
  padding-block: 0.5rem; border-bottom: 1px solid currentColor; }
.content-list__delete, .content-list__publish { display: inline; }
.content-preview__body { border: 1px solid currentColor; padding: 0.5rem; overflow-wrap: anywhere; }
.site-nav { display: flex; flex-wrap: wrap; gap: 0.75rem; }
.content-filters { display: flex; flex-wrap: wrap; gap: 0.75rem; align-items: center; margin-block: 1rem; }
.dashboard-counts { font-size: 1.1rem; }
"""


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


def home_html() -> str:
    """The home page (feed of published Posts), as written to site/index.html."""
    posts = content_module.list_published("post")
    return environment().get_template("public/home.html").render(
        title=settings.SITE_TITLE, items=[
            {"title": post["title"], "href": f"posts/{post['slug']}.html"} for post in posts
        ],
        css_path="style.css", home_path="index.html", nav_items=nav_items(),
    )


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
        **{item_key: item}, body_html=render_markdown(item["body_md"]),
        css_path=f"{prefix}style.css", home_path=f"{prefix}index.html",
        nav_items=nav_items(prefix=prefix),
    )


def _write(path: Path, text: str) -> None:
    # Explicit UTF-8: the pages declare <meta charset="utf-8">, and the
    # platform default (cp1252 on Windows) can't encode an emoji at all.
    path.write_text(text, encoding="utf-8")


def render_site(out: Path | None = None) -> Path:
    out = out or settings.SITE
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    _write(out / "style.css", CSS)
    _write(out / "index.html", home_html())

    posts_dir = out / "posts"
    posts_dir.mkdir()
    for post in content_module.list_published("post"):
        _write(posts_dir / f"{post['slug']}.html", post_html(post))
    for page in _exportable_pages():
        _write(out / f"{page['slug']}.html", page_html(page))

    return out
