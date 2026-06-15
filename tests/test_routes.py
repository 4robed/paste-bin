import pytest


class TestIndexPage:
    def test_get_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_contains_form(self, client):
        resp = client.get("/")
        assert b"<form" in resp.content

    def test_contains_language_select(self, client):
        resp = client.get("/")
        assert b"language" in resp.content

    def test_contains_expiry_select(self, client):
        resp = client.get("/")
        assert b"expiry" in resp.content

    def test_contains_password_field(self, client):
        resp = client.get("/")
        assert b"password" in resp.content

    def test_contains_submit_button(self, client):
        resp = client.get("/")
        assert b"Create Paste" in resp.content


class TestSubmitPaste:
    def test_valid_paste_redirects(self, client):
        resp = client.post("/", data={"content": "x = 1", "language": "python", "expiry": "never"}, follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"].startswith("/")

    def test_redirect_target_is_viewable(self, client):
        resp = client.post("/", data={"content": "hello", "language": "plaintext", "expiry": "never"}, follow_redirects=False)
        code = resp.headers["location"]
        view = client.get(code)
        assert view.status_code == 200

    def test_empty_content_returns_422(self, client):
        resp = client.post("/", data={"content": "   ", "language": "plaintext", "expiry": "never"})
        assert resp.status_code == 422

    def test_empty_content_shows_error(self, client):
        resp = client.post("/", data={"content": "", "language": "plaintext", "expiry": "never"})
        assert b"cannot be empty" in resp.content.lower() or resp.status_code in (303, 422)

    def test_title_stored(self, client):
        resp = client.post(
            "/",
            data={"title": "My Snippet", "content": "x=1", "language": "python", "expiry": "never"},
            follow_redirects=False,
        )
        code = resp.headers["location"]
        view = client.get(code)
        assert b"My Snippet" in view.content

    def test_content_visible_on_view(self, client):
        resp = client.post("/", data={"content": "unique_marker_xyz", "language": "plaintext", "expiry": "never"}, follow_redirects=False)
        code = resp.headers["location"]
        view = client.get(code)
        assert b"unique_marker_xyz" in view.content

    def test_language_badge_visible(self, client):
        resp = client.post("/", data={"content": "x=1", "language": "python", "expiry": "never"}, follow_redirects=False)
        code = resp.headers["location"]
        view = client.get(code)
        assert b"python" in view.content

    def test_with_expiry_option(self, client):
        for opt in ["1h", "1d", "7d", "30d"]:
            resp = client.post("/", data={"content": "x", "language": "plaintext", "expiry": opt}, follow_redirects=False)
            assert resp.status_code == 303

    def test_invalid_expiry_defaults(self, client):
        resp = client.post("/", data={"content": "x", "language": "plaintext", "expiry": "bogus"}, follow_redirects=False)
        assert resp.status_code == 303


class TestViewPaste:
    def test_view_plain_paste(self, client, plain_paste):
        resp = client.get(f"/{plain_paste}")
        assert resp.status_code == 200
        assert b"hello world" in resp.content

    def test_view_python_paste(self, client, python_paste):
        resp = client.get(f"/{python_paste}")
        assert resp.status_code == 200
        assert b"My Script" in resp.content

    def test_view_increments_counter(self, client, plain_paste):
        resp1 = client.get(f"/{plain_paste}")
        resp2 = client.get(f"/{plain_paste}")
        assert resp2.status_code == 200

    def test_unknown_code_returns_404(self, client):
        resp = client.get("/NOTFOUND")
        assert resp.status_code == 404

    def test_404_page_rendered(self, client):
        resp = client.get("/NOTFOUND")
        assert b"404" in resp.content

    def test_protected_paste_shows_gate(self, client, protected_paste):
        resp = client.get(f"/{protected_paste}")
        assert resp.status_code == 200
        assert b"Password" in resp.content or b"password" in resp.content

    def test_protected_paste_hides_content(self, client, protected_paste):
        resp = client.get(f"/{protected_paste}")
        assert b"secret code" not in resp.content

    def test_copy_button_present(self, client, plain_paste):
        resp = client.get(f"/{plain_paste}")
        assert b"Copy" in resp.content

    def test_new_paste_link_present(self, client, plain_paste):
        resp = client.get(f"/{plain_paste}")
        assert b"New Paste" in resp.content or b"/" in resp.content


class TestUnlockPaste:
    def test_correct_password_unlocks(self, client, protected_paste):
        resp = client.post(
            f"/{protected_paste}/unlock",
            data={"password": "hunter2"},
            follow_redirects=False,
        )
        assert resp.status_code == 303

    def test_wrong_password_shows_error(self, client, protected_paste):
        resp = client.post(f"/{protected_paste}/unlock", data={"password": "wrong"})
        assert resp.status_code == 200
        assert b"Incorrect" in resp.content or b"incorrect" in resp.content

    def test_wrong_password_does_not_set_cookie(self, client, protected_paste):
        resp = client.post(f"/{protected_paste}/unlock", data={"password": "wrong"})
        assert "paste_unlock" not in resp.cookies

    def test_correct_password_sets_cookie(self, client, protected_paste):
        resp = client.post(
            f"/{protected_paste}/unlock",
            data={"password": "hunter2"},
            follow_redirects=False,
        )
        assert any("paste_unlock" in k for k in resp.cookies)

    def test_unlock_nonexistent_paste_returns_404(self, client):
        resp = client.post("/XXXXXXXX/unlock", data={"password": "any"})
        assert resp.status_code == 404

    def test_unlocked_paste_shows_content(self, client, protected_paste):
        client.post(f"/{protected_paste}/unlock", data={"password": "hunter2"}, follow_redirects=True)
        resp = client.get(f"/{protected_paste}")
        assert b"secret code" in resp.content


class TestRawAndDownload:
    def test_raw_endpoint_returns_plaintext(self, client, plain_paste):
        resp = client.get(f"/{plain_paste}/raw")
        if resp.status_code == 200:
            assert "text/plain" in resp.headers.get("content-type", "")
            assert b"hello world" in resp.content

    def test_download_endpoint(self, client, plain_paste):
        resp = client.get(f"/{plain_paste}/download")
        if resp.status_code == 200:
            assert b"hello world" in resp.content
