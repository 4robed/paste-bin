import pytest


class TestApiCreatePaste:
    def test_returns_201_or_200(self, client):
        resp = client.post("/api/pastes", json={"content": "x = 1", "language": "python"})
        assert resp.status_code in (200, 201)

    def test_returns_short_code(self, client):
        resp = client.post("/api/pastes", json={"content": "x = 1", "language": "python"})
        data = resp.json()
        assert "short_code" in data
        assert len(data["short_code"]) == 8

    def test_returns_url(self, client):
        resp = client.post("/api/pastes", json={"content": "x = 1", "language": "python"})
        data = resp.json()
        assert "url" in data
        assert data["short_code"] in data["url"]

    def test_returns_language(self, client):
        resp = client.post("/api/pastes", json={"content": "x = 1", "language": "python"})
        assert resp.json()["language"] == "python"

    def test_returns_is_protected_false_for_public(self, client):
        resp = client.post("/api/pastes", json={"content": "x"})
        assert resp.json()["is_protected"] is False

    def test_returns_is_protected_true_for_password(self, client):
        resp = client.post("/api/pastes", json={"content": "x", "password": "secret"})
        assert resp.json()["is_protected"] is True

    def test_content_not_returned_as_password_hash(self, client):
        resp = client.post("/api/pastes", json={"content": "x", "password": "secret"})
        assert "password_hash" not in resp.json()
        assert "password" not in resp.json()

    def test_with_title(self, client):
        resp = client.post("/api/pastes", json={"content": "x", "title": "API Test"})
        assert resp.json()["title"] == "API Test"

    def test_default_language_is_plaintext(self, client):
        resp = client.post("/api/pastes", json={"content": "x"})
        assert resp.json()["language"] == "plaintext"

    def test_never_expiry_returns_null(self, client):
        resp = client.post("/api/pastes", json={"content": "x", "expiry": "never"})
        assert resp.json()["expires_at"] is None

    def test_1d_expiry_returns_datetime(self, client):
        resp = client.post("/api/pastes", json={"content": "x", "expiry": "1d"})
        assert resp.json()["expires_at"] is not None

    def test_empty_content_returns_422(self, client):
        resp = client.post("/api/pastes", json={"content": ""})
        assert resp.status_code == 422

    def test_whitespace_only_content_returns_422(self, client):
        resp = client.post("/api/pastes", json={"content": "   "})
        assert resp.status_code == 422

    def test_missing_content_returns_422(self, client):
        resp = client.post("/api/pastes", json={"language": "python"})
        assert resp.status_code == 422

    def test_views_starts_at_zero(self, client):
        resp = client.post("/api/pastes", json={"content": "x"})
        assert resp.json()["views"] == 0

    def test_all_language_options(self, client):
        langs = ["python", "javascript", "typescript", "go", "rust", "sql", "bash", "plaintext"]
        for lang in langs:
            resp = client.post("/api/pastes", json={"content": f"// {lang}", "language": lang})
            assert resp.status_code in (200, 201)
            assert resp.json()["language"] == lang


class TestApiGetPaste:
    def test_get_existing_paste(self, client):
        create = client.post("/api/pastes", json={"content": "hello api", "language": "python"})
        code = create.json()["short_code"]
        resp = client.get(f"/api/pastes/{code}")
        assert resp.status_code == 200
        assert resp.json()["content"] == "hello api"

    def test_get_unknown_code_returns_404(self, client):
        resp = client.get("/api/pastes/XXXXXXXX")
        assert resp.status_code == 404

    def test_get_protected_paste_without_cookie_returns_403(self, client):
        create = client.post("/api/pastes", json={"content": "secret", "password": "pw"})
        code = create.json()["short_code"]
        resp = client.get(f"/api/pastes/{code}")
        assert resp.status_code == 403

    def test_response_includes_all_fields(self, client):
        create = client.post("/api/pastes", json={"content": "x", "language": "go", "title": "GoSnip"})
        code = create.json()["short_code"]
        resp = client.get(f"/api/pastes/{code}")
        data = resp.json()
        for field in ["short_code", "title", "content", "language", "views", "created_at", "expires_at", "is_protected"]:
            assert field in data, f"Missing field: {field}"

    def test_get_returns_correct_short_code(self, client):
        create = client.post("/api/pastes", json={"content": "x"})
        code = create.json()["short_code"]
        resp = client.get(f"/api/pastes/{code}")
        assert resp.json()["short_code"] == code
