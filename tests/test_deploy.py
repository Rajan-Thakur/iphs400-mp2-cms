"""`cms deploy` pushes site/ to the gh-pages branch (T07). Exercised for real
against a throwaway git repo whose `origin` is a local bare repository, so
nothing ever leaves the machine.
"""
from __future__ import annotations

import shutil
import subprocess

import pytest

from app import cli, settings
from app import content as content_module
from app import db as db_module
from tests.conftest import DEMO_USERS

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")


def _git(*args: str, cwd) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True,
                          capture_output=True, text=True, encoding="utf-8").stdout


@pytest.fixture
def project(tmp_path, monkeypatch):
    """An empty git checkout (site/ not yet published) with a local bare
    `origin`, and the working directory moved into it -- ghp-import acts on
    the current directory's repo."""
    for var, value in {"GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.test",
                       "GIT_COMMITTER_NAME": "Test",
                       "GIT_COMMITTER_EMAIL": "test@example.test"}.items():
        monkeypatch.setenv(var, value)
    # These would point git (and so ghp-import's push) at some other repo --
    # e.g. the real one, when pytest runs from a git hook. Never inherit them.
    for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
        monkeypatch.delenv(var, raising=False)
    origin = tmp_path / "origin.git"
    repo = tmp_path / "repo"
    _git("init", "--bare", str(origin), cwd=tmp_path)
    _git("init", str(repo), cwd=tmp_path)
    site = repo / "site"
    monkeypatch.setattr(settings, "SITE", site)
    monkeypatch.chdir(repo)
    return {"repo": repo, "origin": origin, "site": site}


def _publish_a_post(title: str) -> None:
    conn = db_module.connect()
    try:
        author = conn.execute("SELECT id FROM users WHERE email = ?",
                                   (DEMO_USERS["admin"]["email"],)).fetchone()["id"]
    finally:
        conn.close()
    post_id = content_module.create_content("post", title, "deployed", "Body.", author)
    content_module.set_status(post_id, "post", content_module.STATUS_PUBLISHED)


def test_publish_then_deploy_puts_current_content_on_gh_pages(project, capsys):
    _git("remote", "add", "origin", str(project["origin"]), cwd=project["repo"])
    _publish_a_post("Fresh off the press")

    assert cli.main(["publish"]) == 0
    assert cli.main(["deploy"]) == 0

    home = _git("show", "gh-pages:index.html", cwd=project["origin"])
    assert "Fresh off the press" in home
    assert "Fresh off the press" in _git("show", "gh-pages:posts/deployed.html",
                                         cwd=project["origin"])
    assert "Pushed to gh-pages" in capsys.readouterr().out


def test_deploy_without_a_published_site_explains_what_to_do(project, capsys):
    assert cli.main(["deploy"]) == 1
    assert "run `uv run cms publish` first" in capsys.readouterr().out


def test_a_failed_push_is_reported_as_a_failure(project, capsys):
    assert cli.main(["publish"]) == 0
    # No `origin` remote, so the push can't succeed.
    assert cli.main(["deploy"]) != 0
    assert "Pushed to gh-pages" not in capsys.readouterr().out
