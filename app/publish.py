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
body { font: 16px/1.6 system-ui, sans-serif; margin: 0 auto; max-width: 42rem; padding: 1rem; }
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
    pages = content_module.list_published("page")
    return [{"title": page["title"], "href": f"{prefix}{page['slug']}.html"} for page in pages]


def _feed_items(posts: list) -> list[dict[str, str]]:
    return [{"title": post["title"], "href": f"posts/{post['slug']}.html"} for post in posts]


def _write_detail_pages(
    env: Environment, out_dir: Path, *, template_name: str, items: list, item_key: str,
    prefix: str, css_path: str, home_path: str,
) -> None:
    """Write one file per item using its detail template (public/post.html
    or public/page.html) — the two loops render_site() needs are identical
    apart from which key the item is passed under and the relative depth."""
    template = env.get_template(template_name)
    for item in items:
        (out_dir / f"{item['slug']}.html").write_text(
            template.render(
                title=item["title"], site_title=settings.SITE_TITLE,
                **{item_key: item}, body_html=render_markdown(item["body_md"]),
                css_path=css_path, home_path=home_path, nav_items=nav_items(prefix=prefix),
            )
        )


def render_site(out: Path | None = None) -> Path:
    out = out or settings.SITE
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    env = environment()
    (out / "style.css").write_text(CSS)

    posts = content_module.list_published("post")
    pages = content_module.list_published("page")

    (out / "index.html").write_text(
        env.get_template("public/home.html").render(
            title=settings.SITE_TITLE, items=_feed_items(posts),
            css_path="style.css", home_path="index.html", nav_items=nav_items(),
        )
    )

    posts_dir = out / "posts"
    posts_dir.mkdir()
    _write_detail_pages(
        env, posts_dir, template_name="public/post.html", items=posts, item_key="post",
        prefix="../", css_path="../style.css", home_path="../index.html",
    )
    _write_detail_pages(
        env, out, template_name="public/page.html", items=pages, item_key="page",
        prefix="", css_path="style.css", home_path="index.html",
    )

    return out
