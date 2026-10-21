"""Markdown -> sanitized HTML: the one pipeline the admin preview and the
later static export (T07) both reuse, so a post can't render one way in the
editor and another way once published. The one deliberate difference is a
link to the site root, which the export makes relative (`to_root` below).
Both make a Media library image (`media/<file>`) relative to the page it is
shown on. `render_text` reads the same Markdown as plain text, for the
search index's excerpts.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from html import unescape

import nh3
from markdown_it import MarkdownIt

_md = MarkdownIt("commonmark")

# What a browser ignores before it reads a URL (WHATWG URL parsing): spaces
# and control characters at either end, and tabs and newlines anywhere.
_TRIMMED = "".join(chr(code) for code in range(0x21))
_DROPPED = {ord("\t"): None, ord("\n"): None, ord("\r"): None}

# Tags a browser breaks the line at. render_text puts a space before each, so
# raw HTML like "<div>alpha</div><div>beta</div>" reads "alpha beta".
_LINE_ENDING_TAG = re.compile(
    r"<(?:br|hr|/?(?:p|div|li|dt|dd|h[1-6]|td|th|tr|table|ul|ol|dl|blockquote|pre))\b",
    re.IGNORECASE,
)


def render_markdown(
    raw: str, *, to_root: str | None = None, media_root: str | None = None,
) -> str:
    """Render Markdown to HTML, then strip anything unsafe (script tags,
    event-handler attributes like onerror=, javascript: URLs, ...).

    `to_root` is set when the HTML is written into site/: the "../" steps
    from that file back to the site root ("" for a Page, "../" for a Post).
    A link written in a body from the site root (`/contact-us.html`), and a
    library snippet's image (`media/team.png`), are then made relative to the
    file, because GitHub Pages serves the site from a subfolder.

    Unset (the admin preview), links stay as written: the admin server
    serves the public pages at its own root, so they resolve there. Only a
    `media/` URL is rewritten, by `media_root`: the "../" steps from the admin
    page the preview is shown on back to the server root, which serves media/.
    """
    html = _md.render(raw)
    if to_root is not None:
        return nh3.clean(html, attribute_filter=_link_rewriter(to_root, root_links=True))
    if media_root is not None:
        return nh3.clean(html, attribute_filter=_link_rewriter(media_root, root_links=False))
    return nh3.clean(html)


def render_text(raw: str) -> str:
    """The words of `raw` as a reader sees them on the page, with no markup:
    every tag dropped (a <script> or <style> with its contents), entities
    decoded, and whitespace runs collapsed to one space.

    The result is plain text, not HTML: a body that shows `<img ...>` as code
    gives those characters back. Show it with textContent or escape it."""
    html = _LINE_ENDING_TAG.sub(lambda tag: " " + tag.group(0), _md.render(raw))
    text = nh3.clean(html, tags=set())
    return " ".join(unescape(text).split())


def _link_rewriter(to_root: str, *, root_links: bool) -> Callable[[str, str, str], str]:
    """An nh3 attribute filter that makes every href/src starting `media/`
    relative to the page, and, with `root_links`, every one a browser would
    read as root-absolute or protocol-relative too.

    nh3 checks URL schemes before it calls the filter, never after, so a
    rewritten value must never be able to start a scheme: it always begins
    with "./", "../" or "https://". Dropping only the "/" would turn
    "/javascript:alert(1)" into a live javascript: link.
    """
    prefix = to_root or "./"

    def rewrite(tag: str, attribute: str, value: str) -> str:
        if attribute not in ("href", "src"):
            return value
        url = value.strip(_TRIMMED).translate(_DROPPED).replace("\\", "/")
        if url.startswith("media/"):
            return prefix + url  # a Media library snippet names it from the site root
        if not root_links:
            return value
        if url.startswith("//"):
            return "https:" + url  # protocol-relative; GitHub Pages is HTTPS-only
        if url.startswith("/"):
            rest = url[1:]
            if rest == "" or rest[0] in "#?":
                rest = "index.html" + rest  # "/" is the home page
            return prefix + rest
        return value

    return rewrite
