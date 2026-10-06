"""T07: publish and export pipeline (ticket #8). Extends the render_site()
pattern tests/test_t00.py established: call render_site(), assert on the
filesystem output it produces.
"""
from __future__ import annotations

from app import content as content_module
from app import db as db_module
from app.publish import render_site


def _admin_id() -> int:
    conn = db_module.connect()
    try:
        return conn.execute(
            "SELECT id FROM users WHERE email = 'admin@example.test'"
        ).fetchone()["id"]
    finally:
        conn.close()


def _seed(kind: str, title: str, slug: str, body_md: str, status: str) -> int:
    content_id = content_module.create_content(kind, title, slug, body_md, _admin_id())
    if status == "published":
        content_module.set_status(content_id, kind, "published")
    return content_id


def test_publish_writes_one_file_per_published_post_and_page(tmp_path):
    _seed("post", "Live Post", "live-post", "Body.", "published")
    _seed("page", "Live Page", "live-page", "Body.", "published")

    out = render_site(tmp_path / "site")
    assert (out / "posts" / "live-post.html").exists()
    assert (out / "live-page.html").exists()


def test_no_draft_appears_anywhere_in_site(tmp_path):
    _seed("post", "Live Post", "live-post", "Body.", "published")
    _seed("post", "Secret Draft Post", "secret-draft-post", "Body.", "draft")
    _seed("page", "Live Page", "live-page", "Body.", "published")
    _seed("page", "Secret Draft Page", "secret-draft-page", "Body.", "draft")

    out = render_site(tmp_path / "site")
    assert not (out / "posts" / "secret-draft-post.html").exists()
    assert not (out / "secret-draft-page.html").exists()

    all_html = "\n".join(p.read_text() for p in out.rglob("*.html"))
    assert "Secret Draft Post" not in all_html
    assert "Secret Draft Page" not in all_html


def test_every_exported_href_and_src_is_relative(tmp_path):
    _seed("post", "Live Post", "live-post", "Body.", "published")
    _seed("page", "Live Page", "live-page", "Body.", "published")

    out = render_site(tmp_path / "site")
    html_files = list(out.rglob("*.html"))
    assert len(html_files) >= 3  # index + 1 post + 1 page
    for path in html_files:
        html = path.read_text()
        assert 'href="/' not in html, f"{path} has a root-absolute href"
        assert 'src="/' not in html, f"{path} has a root-absolute src"


def test_home_feed_lists_published_posts_with_relative_links(tmp_path):
    _seed("post", "Live Post", "live-post", "Body.", "published")
    _seed("post", "Draft Post", "draft-post", "Body.", "draft")

    out = render_site(tmp_path / "site")
    html = (out / "index.html").read_text()
    assert "Live Post" in html
    assert "Draft Post" not in html
    assert 'href="posts/live-post.html"' in html


def test_post_detail_page_links_back_up_one_level(tmp_path):
    _seed("post", "Live Post", "live-post", "Body.", "published")
    _seed("page", "Live Page", "live-page", "Body.", "published")

    out = render_site(tmp_path / "site")
    html = (out / "posts" / "live-post.html").read_text()
    assert 'href="../index.html"' in html
    assert 'href="../style.css"' in html
    assert 'href="../live-page.html"' in html  # nav still lists the published Page


def test_exported_markdown_is_rendered_and_sanitized(tmp_path):
    _seed("post", "Dangerous Post", "dangerous-post",
          "# Hi\n\n<script>alert(1)</script><img src=x onerror=alert(1)>", "published")

    out = render_site(tmp_path / "site")
    html = (out / "posts" / "dangerous-post.html").read_text()
    assert "<h1>Hi</h1>" in html
    assert "<script" not in html
    assert "onerror" not in html


def test_exported_page_markdown_is_also_sanitized(tmp_path):
    # T09: re-verify sanitization on the Page export path too, not just Posts
    # (#4 only ever tested the admin preview; #7/#8 added the export itself).
    _seed("page", "Dangerous Page", "dangerous-page",
          "# Hi\n\n<script>alert(1)</script><img src=x onerror=alert(1)>", "published")

    out = render_site(tmp_path / "site")
    html = (out / "dangerous-page.html").read_text()
    assert "<h1>Hi</h1>" in html
    assert "<script" not in html
    assert "onerror" not in html


def test_post_and_page_header_shows_site_title_not_the_items_own_title(tmp_path):
    from app import settings

    _seed("post", "Live Post", "live-post", "Body.", "published")
    _seed("page", "Live Page", "live-page", "Body.", "published")

    out = render_site(tmp_path / "site")
    post_html = (out / "posts" / "live-post.html").read_text()
    page_html = (out / "live-page.html").read_text()

    # The page <title> tag is item-specific, but the header brand link must
    # stay the site's own name, not get overwritten by the item's title.
    assert f"<title>Live Post</title>" in post_html
    assert f'index.html">{settings.SITE_TITLE}</a>' in post_html
    assert f"<title>Live Page</title>" in page_html
    assert f'index.html">{settings.SITE_TITLE}</a>' in page_html


def test_non_ascii_content_exports_as_utf8(tmp_path):
    # T10: write_text used the platform default (cp1252 on Windows), which
    # crashed on an emoji and mangled accented characters.
    _seed("post", "Café 🎉", "cafe", "Ünïcödé body — with an em dash 🎉", "published")

    out = render_site(tmp_path / "site")
    html = (out / "posts" / "cafe.html").read_bytes().decode("utf-8")
    assert "Café 🎉" in html
    assert "Ünïcödé body — with an em dash 🎉" in html
    (out / "style.css").read_bytes().decode("utf-8")  # the CSS has an em dash too


def test_a_published_page_with_a_reserved_slug_never_overwrites_the_home_page(tmp_path):
    # Simulates a row saved before the editor refused reserved slugs.
    _seed("post", "Live Post", "live-post", "Body.", "published")
    _seed("page", "Imposter Home", "index", "Body.", "published")

    out = render_site(tmp_path / "site")
    home = (out / "index.html").read_text(encoding="utf-8")
    assert 'href="posts/live-post.html"' in home  # still the real home page
    assert "Imposter Home" not in home  # and not linked from the nav either


def test_running_publish_twice_reflects_current_content_not_stale_output(tmp_path):
    post_id = _seed("post", "Will Be Unpublished", "will-be-unpublished", "Body.", "published")
    site_dir = tmp_path / "site"
    render_site(site_dir)
    assert (site_dir / "posts" / "will-be-unpublished.html").exists()

    content_module.set_status(post_id, "post", "draft")
    render_site(site_dir)
    assert not (site_dir / "posts" / "will-be-unpublished.html").exists()
