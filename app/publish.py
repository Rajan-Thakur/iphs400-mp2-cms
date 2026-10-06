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
"""


def environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(settings.TEMPLATES)),
        autoescape=select_autoescape(["html"]),
    )


def nav_items() -> list[dict[str, str]]:
    """Published Pages, as relative (title, href) links for the public
    site's nav. The linked file itself is written by the full export
    (T07) — a draft Page never appears here."""
    pages = content_module.list_published("page")
    return [{"title": page["title"], "href": f"{page['slug']}.html"} for page in pages]


def render_site(out: Path | None = None) -> Path:
    out = out or settings.SITE
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    env = environment()
    (out / "style.css").write_text(CSS)
    (out / "index.html").write_text(
        env.get_template("public/home.html").render(
            title=settings.SITE_TITLE, items=[], css_path="style.css",
            home_path="index.html", nav_items=nav_items(),
        )
    )
    return out
