"""Markdown -> sanitized HTML: the one pipeline the admin preview and the
later static export (T07) both reuse, so a post can't render one way in the
editor and another way once published. The one deliberate difference is a
link to the site root, which the export makes relative (`to_root` below).
"""
from __future__ import annotations

from collections.abc import Callable

import nh3
from markdown_it import MarkdownIt

_md = MarkdownIt("commonmark")

# What a browser ignores before it reads a URL (WHATWG URL parsing): spaces
# and control characters at either end, and tabs and newlines anywhere.
_TRIMMED = "".join(chr(code) for code in range(0x21))
_DROPPED = {ord("\t"): None, ord("\n"): None, ord("\r"): None}


def render_markdown(raw: str, *, to_root: str | None = None) -> str:
    """Render Markdown to HTML, then strip anything unsafe (script tags,
    event-handler attributes like onerror=, javascript: URLs, ...).

    `to_root` is set when the HTML is written into site/: the "../" steps
    from that file back to the site root ("" for a Page, "../" for a Post).
    A link written in a body from the site root (`/contact-us.html`) is then
    made relative to the file, because GitHub Pages serves the site from a
    subfolder. Unset (the admin preview), links stay as written: the admin
    server serves the public pages at its own root, so they resolve there.
    """
    html = _md.render(raw)
    if to_root is None:
        return nh3.clean(html)
    return nh3.clean(html, attribute_filter=_root_link_rewriter(to_root))


def _root_link_rewriter(to_root: str) -> Callable[[str, str, str], str]:
    """An nh3 attribute filter that rewrites every href/src a browser would
    read as root-absolute or protocol-relative.

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
        if url.startswith("//"):
            return "https:" + url  # protocol-relative; GitHub Pages is HTTPS-only
        if url.startswith("/"):
            rest = url[1:]
            if rest == "" or rest[0] in "#?":
                rest = "index.html" + rest  # "/" is the home page
            return prefix + rest
        return value

    return rewrite
