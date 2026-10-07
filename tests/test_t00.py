"""T00: the walking skeleton. These pass in the fresh template.

Do not delete them. If a change breaks them, the change broke the app's front
door.
"""


def test_admin_console_answers(client_as):
    # T02 put /admin behind a login guard, and T08 replaced the original
    # placeholder page with a real dashboard (content counts by status).
    # The "front door" this test checks is now: a logged-in Editor or Admin
    # reaching a real dashboard, not the literal placeholder text T00 shipped
    # with (see tests/test_roles.py for the anonymous-gets-redirected case).
    response = client_as("editor").get("/admin")
    assert response.status_code == 200
    assert "dashboard" in response.text.lower()


def test_public_home_answers(client):
    response = client.get("/")
    assert response.status_code == 200


def test_publish_writes_a_site(tmp_path):
    from app.publish import render_site

    out = render_site(tmp_path / "site")
    assert (out / "index.html").exists() and (out / "style.css").exists()


def test_published_html_uses_relative_paths(tmp_path):
    """Root-absolute paths break on GitHub Pages project URLs (rubric F2)."""
    from app.publish import render_site

    html = (render_site(tmp_path / "site") / "index.html").read_text(encoding="utf-8")
    assert 'href="/' not in html and 'src="/' not in html
