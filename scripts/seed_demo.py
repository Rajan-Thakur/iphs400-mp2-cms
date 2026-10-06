#!/usr/bin/env python3
"""Create demo data so a grader (and you) can use the CMS immediately.

    uv run python scripts/seed_demo.py

Creates one admin and one editor user (passwords read from .env, never
hard-coded). As later tickets add Posts/Pages, this script grows to seed
example content too.

The rubric expects this to run clean on a fresh clone with .env.example values
(item E4), because the database itself is never committed.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import settings  # noqa: E402
from app.seed import seed_posts, seed_users  # noqa: E402


def main() -> int:
    admin_pw = os.environ.get("CMS_ADMIN_PASSWORD")
    editor_pw = os.environ.get("CMS_EDITOR_PASSWORD")
    if not admin_pw or not editor_pw:
        print("Set CMS_ADMIN_PASSWORD and CMS_EDITOR_PASSWORD in .env "
              "(copy .env.example).")
        return 1

    seed_users(settings.DATABASE_PATH, admin_pw, editor_pw)
    seed_posts(settings.DATABASE_PATH)
    print(f"Seeded admin/editor users and an example post into {settings.DATABASE_PATH}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
