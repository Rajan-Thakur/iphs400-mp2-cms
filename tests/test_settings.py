"""T10: settings read .env, so `cp .env.example .env` is the whole setup (ticket #11)."""
from __future__ import annotations

import os

import pytest

from app import settings


@pytest.fixture
def isolated_environ(monkeypatch):
    env = os.environ.copy()
    monkeypatch.setattr(os, "environ", env)
    return env


def test_load_dotenv_sets_variables_that_are_not_already_set(tmp_path, isolated_environ):
    isolated_environ.pop("CMS_ADMIN_PASSWORD", None)
    env_file = tmp_path / ".env"
    env_file.write_text("CMS_ADMIN_PASSWORD=from-dotenv\n", encoding="utf-8")

    settings.load_dotenv(env_file)
    assert isolated_environ["CMS_ADMIN_PASSWORD"] == "from-dotenv"


def test_real_environment_variables_override_dotenv(tmp_path, isolated_environ):
    isolated_environ["CMS_ADMIN_PASSWORD"] = "from-shell"
    env_file = tmp_path / ".env"
    env_file.write_text("CMS_ADMIN_PASSWORD=from-dotenv\n", encoding="utf-8")

    settings.load_dotenv(env_file)
    assert isolated_environ["CMS_ADMIN_PASSWORD"] == "from-shell"


def test_load_dotenv_skips_comments_and_blanks_and_strips_quotes(tmp_path, isolated_environ):
    for key in ("A_KEY", "B_KEY", "EMPTY_KEY"):
        isolated_environ.pop(key, None)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# a comment\n\nA_KEY = spaced value \nB_KEY=\"quoted value\"\nEMPTY_KEY=\nnot a pair\n",
        encoding="utf-8",
    )

    settings.load_dotenv(env_file)
    assert isolated_environ["A_KEY"] == "spaced value"
    assert isolated_environ["B_KEY"] == "quoted value"
    assert isolated_environ["EMPTY_KEY"] == ""
    assert "not a pair" not in isolated_environ


def test_load_dotenv_handles_a_utf8_bom(tmp_path, isolated_environ):
    # PowerShell's Out-File writes a BOM; it must not glue onto the first key.
    isolated_environ.pop("BOM_FIRST_KEY", None)
    env_file = tmp_path / ".env"
    env_file.write_bytes("﻿BOM_FIRST_KEY=value\n".encode("utf-8"))

    settings.load_dotenv(env_file)
    assert isolated_environ["BOM_FIRST_KEY"] == "value"


def test_missing_dotenv_is_a_no_op(tmp_path, isolated_environ):
    before = dict(isolated_environ)
    settings.load_dotenv(tmp_path / "does-not-exist.env")
    assert isolated_environ == before


def test_relative_database_path_resolves_against_the_project_root():
    # So `cms serve` and scripts/seed_demo.py share one file whatever the cwd.
    assert settings._project_path("cms.db") == settings.ROOT / "cms.db"
    assert settings._project_path(str(settings.ROOT / "x.db")) == settings.ROOT / "x.db"
