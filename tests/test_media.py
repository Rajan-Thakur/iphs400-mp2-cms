"""MP2plus F1: media uploads with alt text (issue #21).

An Editor or Admin uploads a PNG or JPEG of 2 MB or less, with alt text, to
the media library; copies the item's Markdown snippet, `![alt](media/<file>)`,
into a Post; and `cms publish` copies media/ into site/media/ with each
`<img src>` made relative to the page it is on. Each test is named after the
acceptance step on #21 it checks.
"""
from __future__ import annotations

import builtins
import re
import shutil
import struct
import subprocess
import zlib
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import pytest

from app import cli, settings
from tests.conftest import extract_csrf, log_in
from tests.test_phone_width import assert_fits_phone

BASE = "http://testserver"


def _png(width: int = 2, height: int = 2) -> bytes:
    """A real (tiny, red) PNG image, built by hand: no imaging library."""
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data)))

    rows = b"".join(b"\x00" + b"\xff\x00\x00" * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


PNG = _png()
# Starts the way every JPEG does (FF D8 FF); the server never decodes it.
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + bytes(32) + b"\xff\xd9"
ALT = "A red square"


@pytest.fixture
def media_dir():
    """This test's own media/: tests/conftest.py points settings.MEDIA at a
    temp folder, so uploads never land in the real one."""
    return settings.MEDIA


def _upload(client, filename: str, data: bytes, alt: str = ALT, *, csrf: str | None = None):
    """Send the library's upload form, with its own CSRF token unless
    `csrf` says otherwise ("" leaves the token out)."""
    token = extract_csrf(client.get("/admin/media").text) if csrf is None else csrf
    form = {"alt_text": alt}
    if token:
        form["csrf_token"] = token
    return client.post("/admin/media/upload", data=form,
                       files={"image": (filename, data, "application/octet-stream")})


def _img_src(html: str, alt: str) -> str:
    tag = re.search(rf'<img [^>]*alt="{re.escape(alt)}"[^>]*>', html)
    assert tag, f"no image {alt!r} in the page"
    return unescape(re.search(r'src="([^"]*)"', tag.group(0)).group(1))


# -- Step 1: upload a PNG or JPEG of 2 MB or less; it appears in the library --

@pytest.mark.parametrize("role", ["admin", "editor"])
@pytest.mark.parametrize("filename", ["square.png", "photo.jpg", "photo.jpeg"])
def test_step1_png_or_jpeg_with_alt_text_appears_in_the_library(client_as, role, filename):
    data = PNG if filename.endswith(".png") else JPEG
    client = client_as(role)
    library = _upload(client, filename, data)

    assert library.status_code == 200
    assert "Image uploaded" in library.text
    src = _img_src(library.text, ALT)
    assert not src.startswith("/"), src
    image = client.get(urlsplit(urljoin(BASE + "/admin/media", src)).path)
    assert image.status_code == 200
    assert image.content == data


def test_step1_an_anonymous_visitor_can_neither_see_nor_use_the_library(client, client_as):
    _upload(client_as("editor"), "square.png", PNG)

    for response in (client.get("/admin/media", follow_redirects=False),
                     client.get("/media/square.png", follow_redirects=False),
                     client.post("/admin/media/upload", data={"alt_text": ALT},
                                 files={"image": ("x.png", PNG, "image/png")},
                                 follow_redirects=False)):
        assert response.status_code == 303
        assert response.headers["location"] == "/login"


def test_step1_an_upload_without_a_file_is_refused_with_a_message(client_as):
    client = client_as("editor")
    token = extract_csrf(client.get("/admin/media").text)
    refused = client.post("/admin/media/upload", data={"alt_text": ALT, "csrf_token": token})

    assert refused.status_code == 400
    assert "Choose an image" in refused.text


# -- Step 2: an upload with empty alt text is refused with a message --

@pytest.mark.parametrize("alt", ["", "   \n\t "])
def test_step2_empty_alt_text_is_refused_with_a_message(client_as, media_dir, alt):
    client = client_as("editor")
    refused = _upload(client, "square.png", PNG, alt=alt)

    assert refused.status_code == 400
    assert "Add alt text" in refused.text
    assert "No images yet" in refused.text
    assert not media_dir.exists() or not any(media_dir.iterdir())


@pytest.mark.parametrize("alt", [
    "​", "⁠﻿", "­", "ㅤ", "⠀", "​ ​",
], ids=["zero-width-space", "word-joiner-and-bom", "soft-hyphen", "hangul-filler",
        "braille-blank", "spaced-zero-width"])
def test_step2_alt_text_with_nothing_visible_is_refused(client_as, media_dir, alt):
    """A screen reader reads these as nothing, the same as empty alt text."""
    refused = _upload(client_as("editor"), "square.png", PNG, alt=alt)

    assert refused.status_code == 400
    assert "Add alt text" in refused.text
    assert not media_dir.exists() or not any(media_dir.iterdir())


# -- Step 3: wrong type (by extension or by first bytes) or over 2 MB is refused --

TWO_MB = 2 * 1024 * 1024
HTML = b"<!doctype html><script>alert(document.cookie)</script>"


@pytest.mark.parametrize("filename, data, message", [
    ("page.html", HTML, "Only PNG and JPEG images"),
    ("page.png", HTML, "isn't a real PNG image"),
    ("page.jpg", HTML, "isn't a real JPEG image"),
    ("square.jpg", PNG, "isn't a real JPEG image"),
    ("big.png", PNG + bytes(TWO_MB - len(PNG) + 1), "over 2 MB"),
], ids=["html", "html-renamed-png", "html-renamed-jpg", "png-renamed-jpg", "over-2mb"])
def test_step3_wrong_type_or_over_2_mb_is_refused(client_as, media_dir, filename, data, message):
    client = client_as("editor")
    refused = _upload(client, filename, data)

    assert refused.status_code == 400
    assert message in unescape(refused.text)
    assert "No images yet" in refused.text
    assert not media_dir.exists() or not any(media_dir.iterdir())


def test_step3_an_image_of_exactly_2_mb_is_accepted(client_as):
    data = PNG + bytes(TWO_MB - len(PNG))
    library = _upload(client_as("editor"), "big.png", data)

    assert library.status_code == 200
    assert _img_src(library.text, ALT)


# -- Step 4: uploads are stored under media/, and media/ is git-ignored --

def test_step4_an_upload_is_stored_under_media(client_as, media_dir):
    _upload(client_as("editor"), "Team Photo (1).PNG", PNG)

    assert [path.name for path in media_dir.iterdir()] == ["team-photo-1.png"]
    assert (media_dir / "team-photo-1.png").read_bytes() == PNG


def test_step4_media_is_git_ignored():
    if shutil.which("git") is None:
        pytest.skip("needs git")
    result = subprocess.run(["git", "check-ignore", "-q", "media/team.png"],
                            cwd=settings.ROOT)
    assert result.returncode == 0, "media/ is not in .gitignore"


@pytest.mark.parametrize("filename", ["../../escape.png", r"..\..\escape.png", "/tmp/escape.png"])
def test_step4_a_folder_in_the_filename_cannot_escape_media(client_as, media_dir, tmp_path, filename):
    _upload(client_as("editor"), filename, PNG)

    assert [path.name for path in media_dir.iterdir()] == ["escape.png"]
    assert not (tmp_path / "escape.png").exists()
    assert not (tmp_path.parent / "escape.png").exists()


def test_step4_a_write_that_fails_leaves_no_partial_file(client_as, media_dir, monkeypatch):
    """A full disk: the new file in media/ is created, then writing to it
    fails part way. Nothing half-written may stay behind to be published."""
    real_open = builtins.open

    class FullDisk:
        def __init__(self, file):
            self.file = file

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            self.file.close()

        def write(self, data):
            self.file.write(data[:10])
            raise OSError(28, "No space left on device")

    def open_on_a_full_disk(path, mode="r", *args, **kwargs):
        file = real_open(path, mode, *args, **kwargs)
        writing_media = Path(path).parent == media_dir and ("w" in mode or "x" in mode)
        return FullDisk(file) if writing_media else file

    editor = client_as("editor")
    monkeypatch.setattr(builtins, "open", open_on_a_full_disk)

    with pytest.raises(OSError, match="No space left"):
        _upload(editor, "square.png", PNG)
    assert list(media_dir.iterdir()) == []


def test_step4_a_second_image_with_the_same_name_keeps_both(client_as, media_dir):
    client = client_as("editor")
    _upload(client, "square.png", PNG, alt="First square")
    library = _upload(client, "square.png", _png(3, 3), alt="Second square")

    assert sorted(path.name for path in media_dir.iterdir()) == ["square-2.png", "square.png"]
    assert _img_src(library.text, "First square").endswith("media/square.png")
    assert _img_src(library.text, "Second square").endswith("media/square-2.png")


@pytest.mark.parametrize("name", ["page.html", "..%5Csecret.png", "missing.png"])
def test_step4_the_admin_serves_only_images_inside_media(client_as, media_dir, tmp_path, name):
    media_dir.mkdir()
    (media_dir / "page.html").write_bytes(HTML)
    (tmp_path / "secret.png").write_bytes(PNG)

    assert client_as("editor").get(f"/media/{name}").status_code == 404


# -- Step 5: each library item shows a copyable Markdown snippet --

def _snippets(html: str) -> list[str]:
    """The values of the library's read-only snippet fields, in page order."""
    fields = re.findall(r'<input [^>]*class="media-item__snippet"[^>]*>', html)
    return [unescape(re.search(r'value="([^"]*)"', field).group(1)) for field in fields]


def test_step5_each_library_item_shows_a_copyable_markdown_snippet(client_as):
    client = client_as("editor")
    _upload(client, "square.png", PNG)
    library = _upload(client, "Club logo.jpg", JPEG, alt='The "CS Honor Society" logo')

    assert _snippets(library.text) == [
        '![The "CS Honor Society" logo](media/club-logo.jpg)',
        "![A red square](media/square.png)",
    ]
    assert len(re.findall(r"<button [^>]*data-copy", library.text)) == 2, \
        "each snippet has a Copy button"


def _img_alts(html: str) -> list[str]:
    return [unescape(alt) for alt in re.findall(r'<img [^>]*alt="([^"]*)"', html)]


@pytest.mark.parametrize("alt", [
    "team_photo", "5 * 3", "Team [photo]", "R & D", "Tom's \"best\" photo", "a > b", "café",
    "部室の写真",
])
def test_step5_alt_text_markdown_leaves_alone_reaches_the_post_as_typed(client_as, alt):
    editor = client_as("editor")
    snippet = _snippets(_upload(editor, "square.png", PNG, alt=alt).text)[0]
    preview = editor.post("/admin/posts/preview", data={"body_md": snippet})

    assert snippet == f"![{alt}](media/square.png)"
    assert _img_alts(preview.text) == [alt]


@pytest.mark.parametrize("alt", [
    "x*y*z", "_hackathon_", "`code`", "<b>bold</b>", "a ] b", "R &amp; D", "[a](b)",
])
def test_step5_alt_text_that_markdown_would_change_is_refused(client_as, media_dir, alt):
    """Pasted as a snippet, each of these would show different alt text (or
    no image at all), and markdown-it drops even backslash-escaped
    characters from an image's alt, so escaping them can't help."""
    refused = _upload(client_as("editor"), "square.png", PNG, alt=alt)

    assert refused.status_code == 400
    assert "Markdown would change" in unescape(refused.text)
    assert not media_dir.exists() or not any(media_dir.iterdir())


def _error(html: str) -> str:
    match = re.search(r'<p class="error">(.*?)</p>', html, re.DOTALL)
    assert match, "no error message on the page"
    return unescape(match.group(1))


def test_step5_the_refusal_names_a_backslash_when_it_refuses_one(client_as):
    refused = _upload(client_as("editor"), "square.png", PNG, alt=r"C:\pics screenshot")

    assert refused.status_code == 400
    assert "\\" in _error(refused.text)


# -- Step 6: the upload form carries a CSRF token; a POST without it is refused --

def test_step6_the_upload_form_carries_a_csrf_token(client_as):
    library = client_as("editor").get("/admin/media").text
    form = re.search(r'<form [^>]*action="[^"]*admin/media/upload"[^>]*>(.*?)</form>',
                     library, re.DOTALL)

    assert form, "no upload form on the library page"
    assert 'enctype="multipart/form-data"' in form.group(0)
    assert re.search(r'<input type="hidden" name="csrf_token" value="[^"]+"', form.group(1))


@pytest.mark.parametrize("csrf", ["", "forged-token-value"], ids=["missing", "forged"])
def test_step6_an_upload_without_its_csrf_token_is_refused(client_as, media_dir, csrf):
    refused = _upload(client_as("editor"), "square.png", PNG, csrf=csrf)

    assert refused.status_code == 403
    assert "session expired" in refused.text
    assert not media_dir.exists() or not any(media_dir.iterdir())


# -- Step 7: cms publish copies media/ into site/media/; the post's <img> has
#    the alt text and a relative src that loads --

def _new_post_with_snippet(editor, slug: str) -> int:
    """Upload square.png, paste its library snippet into a new Post, and
    return the Post's id, all through the admin screens."""
    snippet = _snippets(_upload(editor, "square.png", PNG).text)[0]
    token = extract_csrf(editor.get("/admin/posts/new").text)
    editor.post("/admin/posts/new", data={
        "title": "Our new logo", "slug": slug, "csrf_token": token,
        "body_md": f"The club has a new logo:\n\n{snippet}\n",
    })
    return int(re.search(r"admin/posts/(\d+)/edit", editor.get("/admin/posts").text).group(1))


def test_step7_publish_copies_media_and_the_posts_img_has_alt_and_a_relative_src(
    client_as, monkeypatch, tmp_path,
):
    post_id = _new_post_with_snippet(client_as("editor"), "new-logo")
    admin = client_as("admin")
    admin.post(f"/admin/posts/{post_id}/publish",
               data={"csrf_token": extract_csrf(admin.get("/admin/posts").text)})
    site = tmp_path / "site"
    monkeypatch.setattr(settings, "SITE", site)

    assert cli.main(["publish"]) == 0

    assert (site / "media" / "square.png").read_bytes() == PNG
    post_page = site / "posts" / "new-logo.html"
    src = _img_src(post_page.read_text(encoding="utf-8"), ALT)
    assert not src.startswith("/") and ":" not in src, f"src {src!r} is not relative"
    assert (post_page.parent / src).resolve() == (site / "media" / "square.png").resolve()


def test_step7_the_dev_servers_post_page_loads_the_image_too(client_as):
    editor = client_as("editor")
    post_id = _new_post_with_snippet(editor, "new-logo")
    admin = client_as("admin")
    admin.post(f"/admin/posts/{post_id}/publish",
               data={"csrf_token": extract_csrf(admin.get("/admin/posts").text)})

    page_url = BASE + "/posts/new-logo.html"
    src = _img_src(editor.get(page_url).text, ALT)
    image = editor.get(urlsplit(urljoin(page_url, src)).path)
    assert image.status_code == 200 and image.content == PNG


@pytest.mark.parametrize("method, path", [
    ("GET", "/admin/posts/{id}/edit"),
    ("POST", "/admin/posts/{id}/revisions/1/rollback"),
], ids=["edit-screen", "refused-roll-back"])
def test_step7_the_editors_preview_loads_the_image(client_as, method, path):
    """The edit screen renders its preview with the page. A refused POST (a
    Roll back with a forged token) renders the same screen two levels deeper."""
    editor = client_as("editor")
    page_path = path.format(id=_new_post_with_snippet(editor, "new-logo"))
    page = editor.request(method, page_path,
                          data={"csrf_token": "forged"} if method == "POST" else None)

    src = _img_src(page.text, ALT)
    image = editor.get(urlsplit(urljoin(BASE + page_path, src)).path)
    assert image.status_code == 200 and image.content == PNG


def test_step7_the_live_preview_places_the_image_for_the_editor_page(client_as):
    """The editor page sends its own `to_root` with the live preview's text."""
    editor = client_as("editor")
    snippet = _snippets(_upload(editor, "square.png", PNG).text)[0]
    live = editor.post("/admin/posts/preview", data={"body_md": snippet, "to_root": "../../"})

    src = _img_src(live.text, ALT)
    image = editor.get(urlsplit(urljoin(BASE + "/admin/posts/new", src)).path)
    assert image.status_code == 200 and image.content == PNG


@pytest.mark.parametrize("to_root", ["javascript:", "https://evil.example/", "/", "..", ".././"])
def test_step7_the_live_preview_ignores_a_to_root_that_is_not_steps_up(client_as, to_root):
    live = client_as("editor").post("/admin/posts/preview", data={
        "body_md": f"![{ALT}](media/square.png)", "to_root": to_root})

    assert _img_src(live.text, ALT) == "media/square.png"


# -- In a real browser (skipped without Chromium) --

def _upload_in_browser(page) -> None:
    page.goto("/admin/media")
    page.set_input_files("input[name=image]", files=[
        {"name": "square.png", "mimeType": "image/png", "buffer": _png(1600, 40)}])
    page.fill("input[name=alt_text]", ALT)
    page.click("form.media-upload button[type=submit]")
    page.wait_for_selector(".success", timeout=5000)


def _wait_for_image(page, selector: str) -> None:
    """Wait until the image at `selector` has loaded: a broken src never does."""
    page.wait_for_function(
        "(selector) => { const img = document.querySelector(selector);"
        " return Boolean(img && img.complete && img.naturalWidth > 0); }",
        arg=selector, timeout=5000)


def test_step1_upload_through_the_form_on_a_phone(phone):
    log_in(phone, "editor")
    _upload_in_browser(phone)

    _wait_for_image(phone, "img.media-item__image")
    assert phone.input_value("input.media-item__snippet") == f"![{ALT}](media/square.png)"
    assert_fits_phone(phone)


def test_step2_the_empty_alt_text_message_shows_on_a_phone(phone):
    log_in(phone, "editor")
    phone.goto("/admin/media")
    phone.set_input_files("input[name=image]", files=[
        {"name": "square.png", "mimeType": "image/png", "buffer": PNG}])
    phone.click("form.media-upload button[type=submit]")

    phone.wait_for_selector(".error", timeout=5000)
    assert "Add alt text" in phone.inner_text(".error")
    assert_fits_phone(phone)


def test_step5_the_copy_button_copies_the_snippet(phone):
    phone.context.grant_permissions(["clipboard-read", "clipboard-write"])
    log_in(phone, "editor")
    _upload_in_browser(phone)
    phone.click("button[data-copy]")

    phone.wait_for_selector("button[data-copy]:has-text('Copied')", timeout=5000)
    assert phone.evaluate("navigator.clipboard.readText()") == f"![{ALT}](media/square.png)"


def test_step7_the_live_preview_shows_the_image_as_you_type(phone):
    log_in(phone, "editor")
    _upload_in_browser(phone)
    snippet = phone.input_value("input.media-item__snippet")
    phone.goto("/admin/posts/new")
    phone.fill("#body_md", f"Our logo:\n\n{snippet}")

    phone.wait_for_selector(f"#preview img[alt='{ALT}']", timeout=5000)
    _wait_for_image(phone, "#preview img")
