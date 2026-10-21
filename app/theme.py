"""The site's Theme (see CONTEXT.md): which stylesheet, of the ones in
app/themes/<name>/style.css, the admin console and the Static export use.

An Admin picks it on the Settings page. The choice is a row in the
database's `settings` table and is read again on every use, so a switch
reaches the next page load and the next `cms publish` with no restart.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app import db as db_module

THEMES_DIR = Path(__file__).with_name("themes")
DEFAULT_THEME = "default"
SETTING_KEY = "theme"

# A stylesheet's description is the first line of its opening /* comment */.
DESCRIPTION_RE = re.compile(r"\s*/\*\s*(.*?)\s*(?:\*/|\n)")


class UnknownTheme(ValueError):
    """A theme name with no app/themes/<name>/style.css."""


@dataclass(frozen=True)
class Theme:
    name: str
    description: str


def _file(name: str) -> Path:
    return THEMES_DIR / name / "style.css"


def names() -> list[str]:
    """Every theme's name, the default first, then A to Z."""
    found = [path.parent.name for path in THEMES_DIR.glob("*/style.css")]
    return sorted(found, key=lambda name: (name != DEFAULT_THEME, name))


def available() -> list[Theme]:
    """Every theme, in names() order, for the Settings page."""
    themes = []
    for name in names():
        match = DESCRIPTION_RE.match(_file(name).read_text(encoding="utf-8"))
        themes.append(Theme(name, match.group(1) if match else ""))
    return themes


def selected() -> str:
    """The stored theme, or the default when none is stored yet or the
    stored one's folder has since been removed."""
    conn = db_module.connect()
    try:
        row = conn.execute("SELECT value FROM settings WHERE key = ?",
                           (SETTING_KEY,)).fetchone()
    except sqlite3.OperationalError:
        # No settings table: a backup from before it existed, copied over
        # the database while the server runs. Every page still gets styled.
        row = None
    finally:
        conn.close()
    return row["value"] if row and row["value"] in names() else DEFAULT_THEME


def select(name: str) -> None:
    """Store `name` as the site's theme. Raises UnknownTheme if there is no
    such theme, so only a real folder's name is ever stored."""
    if name not in names():
        raise UnknownTheme(name)
    conn = db_module.connect()
    try:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
            (SETTING_KEY, name),
        )
        conn.commit()
    finally:
        conn.close()


def stylesheet() -> Path:
    """The selected theme's style.css. Callers copy its bytes as they are,
    so site/style.css matches the file exactly."""
    return _file(selected())
