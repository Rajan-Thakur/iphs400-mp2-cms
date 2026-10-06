"""Configuration, read from the environment (never hard-code secrets).

Values come from real environment variables first, then from `.env` in the
project root, so `cp .env.example .env` is the whole setup. `uv run` does not
load `.env` by itself, and python-dotenv isn't in the fixed stack, hence the
small reader below.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
SITE = ROOT / "site"


def load_dotenv(path: Path) -> None:
    """Copy KEY=VALUE lines from `path` into os.environ, never overriding a
    variable that is already set. Blank lines and # comments are skipped."""
    try:
        # utf-8-sig: PowerShell's Out-File writes a BOM, which would otherwise
        # glue itself onto the first key and silently drop that variable.
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)


load_dotenv(ROOT / ".env")


def _project_path(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


SECRET_KEY = os.environ.get("CMS_SECRET_KEY", "dev-only-not-for-production")
DATABASE_PATH = _project_path(os.environ.get("CMS_DATABASE", "cms.db"))
SITE_TITLE = os.environ.get("CMS_SITE_TITLE", "My CMS")
# Set this to your Pages URL once you deploy, e.g.
# https://yourname.github.io/iphs400-mp2-cms/
BASE_PATH = os.environ.get("CMS_BASE_PATH", "")
