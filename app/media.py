"""The Media library: images uploaded for use in Posts, each with Alt text
(see CONTEXT.md). The file goes in media/, which is git-ignored like the
database; its row in the `media` table keeps the Alt text. No ORM (see spec
Implementation Decisions).
"""
from __future__ import annotations

import itertools
import re
import sqlite3
import unicodedata
from html import unescape
from pathlib import Path, PurePosixPath

from app import db as db_module
from app import settings
from app.mdrender import render_markdown

MAX_BYTES = 2 * 1024 * 1024  # 2 MB

# The extensions accepted, each with the type's name and the first bytes
# every file of that type starts with, so a renamed .html file is caught.
SIGNATURES = {
    ".png": ("PNG", b"\x89PNG\r\n\x1a\n"),
    ".jpg": ("JPEG", b"\xff\xd8\xff"),
    ".jpeg": ("JPEG", b"\xff\xd8\xff"),
}

# Hangul fillers: letters to Unicode, but they show (and read as) nothing.
INVISIBLE_LETTERS = {"ᅟ", "ᅠ", "ㅤ", "ﾠ"}


class UploadRefused(ValueError):
    """An upload that breaks one of the library's rules; the message says
    which, in words for the upload form."""


def snippet(item) -> str:
    """The Markdown that places a library item in a Post."""
    return f"![{item['alt_text']}](media/{item['filename']})"


def clean_alt_text(raw: str) -> str:
    """`raw` on one line, with runs of spaces collapsed. Raises
    UploadRefused if nothing is left, or if a Post would show different
    alt text once the item's snippet is pasted in."""
    alt = " ".join(raw.split())
    if not _has_words(alt):
        raise UploadRefused("Add alt text: a short description of the image for "
                            "someone who can't see it.")
    if _published_alt(alt) != alt:
        raise UploadRefused("Markdown would change this alt text in a post: it reads some "
                            "uses of * _ ` [ ] < & \\ as formatting. Reword it without them.")
    return alt


def _has_words(text: str) -> bool:
    """Whether `text` has a letter or digit a screen reader would read out.
    Zero-width and other invisible characters alone count as empty."""
    return any(unicodedata.category(character)[0] in "LN"
               and character not in INVISIBLE_LETTERS for character in text)


def _published_alt(alt: str) -> str | None:
    """The alt text a Post shows for a snippet carrying `alt`, rendered by
    the Posts' own Markdown pipeline (None if it makes no image at all).
    Markdown reads * _ ` [ ] < & as syntax there, and markdown-it drops even
    backslash-escaped characters from an image's alt, so escaping can't help."""
    html = render_markdown(snippet({"alt_text": alt, "filename": "image.png"}))
    match = re.search(r'<img [^>]*alt="([^"]*)"', html)
    return unescape(match.group(1)) if match else None


def check_image(filename: str, data: bytes) -> str:
    """The lowercase extension of an acceptable image: a PNG or JPEG by both
    its name and its first bytes, MAX_BYTES or smaller. Raises UploadRefused
    otherwise. `data` may be cut short at MAX_BYTES + 1 bytes."""
    if not filename:
        raise UploadRefused("Choose an image to upload.")
    extension = PurePosixPath(filename).suffix.lower()
    if extension not in SIGNATURES:
        raise UploadRefused("Only PNG and JPEG images can be uploaded (.png, .jpg or .jpeg).")
    if len(data) > MAX_BYTES:
        raise UploadRefused("That image is over 2 MB. Make it smaller and upload it again.")
    kind, signature = SIGNATURES[extension]
    if not data.startswith(signature):
        raise UploadRefused(f"That file isn't a real {kind} image, whatever its name says.")
    return extension


def _safe_stem(filename: str) -> str:
    """The upload's own name, without folders or extension, as lowercase
    letters, digits and hyphens: "C:\\pics\\Team Photo (1).PNG" -> "team-photo-1"."""
    stem = PurePosixPath(filename.replace("\\", "/")).stem
    return re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")[:60].strip("-") or "image"


def _create_file(conn: sqlite3.Connection, filename: str, extension: str, data: bytes) -> Path:
    """Write `data` to a new file in media/ named after the upload: "team.png",
    then "team-2.png", "team-3.png", ... It never replaces a file already
    there, even one another upload creates at the same moment, nor takes a
    name the library already uses."""
    stem = _safe_stem(filename)
    taken = {row["filename"] for row in conn.execute("SELECT filename FROM media")}
    for number in itertools.count(1):
        path = settings.MEDIA / (f"{stem}{extension}" if number == 1
                                 else f"{stem}-{number}{extension}")
        if path.name in taken:
            continue
        try:
            file = open(path, "xb")
        except FileExistsError:
            continue
        try:
            with file:
                file.write(data)
        except BaseException:
            path.unlink()  # this upload's own, half-written: never publish it
            raise
        return path


def save_upload(filename: str, data: bytes, alt_text: str, uploaded_by: int) -> str:
    """Write the image to media/ under a safe, unused name and record its
    Alt text in the library. Returns the name it was saved as; raises
    UploadRefused, storing nothing, if the upload breaks a rule."""
    extension = check_image(filename, data)
    alt_text = clean_alt_text(alt_text)
    settings.MEDIA.mkdir(parents=True, exist_ok=True)
    conn = db_module.connect()
    try:
        path = _create_file(conn, filename, extension, data)
        try:
            conn.execute(
                "INSERT INTO media (filename, alt_text, uploaded_by) VALUES (?, ?, ?)",
                (path.name, alt_text, uploaded_by),
            )
            conn.commit()
        except sqlite3.Error:
            path.unlink()  # this upload's own file: _create_file never reuses one
            raise
        return path.name
    finally:
        conn.close()


def list_media() -> list[sqlite3.Row]:
    """Every image in the library, newest first, with who uploaded it."""
    conn = db_module.connect()
    try:
        return conn.execute(
            "SELECT media.*, users.email AS uploaded_by_email FROM media "
            "JOIN users ON users.id = media.uploaded_by ORDER BY media.id DESC"
        ).fetchall()
    finally:
        conn.close()


def served_file(filename: str) -> Path | None:
    """media/<filename>, if that is an image file directly inside media/;
    else None, so a crafted name ("..\\cms.db", "x.html") is never served."""
    if PurePosixPath(filename).suffix.lower() not in SIGNATURES:
        return None
    path = settings.MEDIA / filename
    try:
        inside = path.resolve().parent == settings.MEDIA.resolve()
    except OSError:
        return None
    return path if inside and path.is_file() else None
