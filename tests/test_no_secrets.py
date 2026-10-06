"""No secret has ever been committed, on any branch (T09; rubric D5). Reads
the whole git history, so a secret that was committed and later deleted
still fails. Skips unless this project is its own full (non-shallow) git
checkout, since otherwise there's no complete history to read.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path, PurePosixPath

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Key shapes, written so this file's own source never matches them.
TOKEN_PATTERNS = {
    "OpenAI/Anthropic-style API key": r"\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}",
    "GitHub token": r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}",
    "AWS access key": r"\bAKIA[0-9A-Z]{16}\b",
    "private key": r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----",
}
SECRET_FILE_PATTERNS = (".env", ".env.*", "*.db", "*.sqlite", "*.sqlite3",
                        "*.pem", "*.key", "id_rsa", "id_ed25519")
ALLOWED_FILES = {".env.example"}


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", check=True).stdout


@pytest.fixture(scope="module")
def history():
    if shutil.which("git") is None:
        pytest.skip("needs git")
    try:
        toplevel = Path(_git("rev-parse", "--show-toplevel").strip()).resolve()
    except subprocess.CalledProcessError:
        pytest.skip("not a git checkout")
    if toplevel != ROOT:
        pytest.skip(f"project sits inside another repository ({toplevel})")
    if _git("rev-parse", "--is-shallow-repository").strip() == "true":
        pytest.skip("shallow clone: the full history isn't here to check")
    if not _git("rev-list", "--all", "-n1").strip():
        pytest.skip("no commits yet")
    return _git


def _is_secret_file(path: str) -> bool:
    name = PurePosixPath(path).name
    return name not in ALLOWED_FILES and any(
        PurePosixPath(name).match(pattern) for pattern in SECRET_FILE_PATTERNS)


def test_secret_file_patterns_catch_what_they_should():
    assert _is_secret_file(".env")
    assert _is_secret_file("config/.env.local")
    assert _is_secret_file("cms.db")
    assert not _is_secret_file(".env.example")
    assert not _is_secret_file("app/db.py")


def test_no_env_database_or_key_file_was_ever_committed(history):
    # -z: NUL-separated and unquoted, so spaces and non-ASCII names survive.
    every_path = set(history("log", "--all", "--format=", "--name-only", "-z").split("\0"))
    committed = sorted(path for path in every_path if _is_secret_file(path))
    assert committed == [], f"secret-looking files in git history: {committed}"


def test_no_key_shaped_token_appears_anywhere_in_history(history):
    added_lines = [line for line in history("log", "--all", "-p", "--format=").splitlines()
                   if line.startswith("+") and not line.startswith("+++")]
    found = [(kind, line[:80]) for line in added_lines
             for kind, pattern in TOKEN_PATTERNS.items() if re.search(pattern, line)]
    assert found == [], f"key-shaped tokens in git history: {found}"
