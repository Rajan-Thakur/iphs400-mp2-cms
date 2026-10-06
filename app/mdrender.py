"""Markdown -> sanitized HTML: the one pipeline the admin preview and the
later static export (T07) both reuse, so a post can't render one way in the
editor and another way once published.
"""
from __future__ import annotations

import nh3
from markdown_it import MarkdownIt

_md = MarkdownIt("commonmark")


def render_markdown(raw: str) -> str:
    """Render Markdown to HTML, then strip anything unsafe (script tags,
    event-handler attributes like onerror=, javascript: URLs, ...)."""
    return nh3.clean(_md.render(raw))
