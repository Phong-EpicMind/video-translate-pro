import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")
from fastapi.testclient import TestClient  # noqa: E402

from translatedub import config  # noqa: E402
from translatedub.web.server import create_app  # noqa: E402


@pytest.fixture
def client(isolated_home):
    # local_only guard rejects the TestClient's synthetic host; disable it for tests.
    return TestClient(create_app(local_only=False))


def test_index_ok(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "TranslateDub" in resp.text or "Translate Pro" in resp.text


def test_get_config_no_secret(client):
    resp = client.get("/api/config")
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_gemini_key"] is False
    assert "gemini_key" not in body


def test_post_config_requires_gemini_when_no_free_engines(client, monkeypatch):
    from translatedub.core.providers import asr, translate
    monkeypatch.setattr(asr.REGISTRY["whisper"], "is_available", lambda cfg: (False, "x"))
    monkeypatch.setattr(translate.REGISTRY["google_free"], "is_available",
                        lambda cfg: (False, "x"))
    resp = client.post("/api/config", json={"target_lang": "en"})
    assert resp.status_code == 400


def test_post_config_allows_keyless_when_free_available(client, monkeypatch):
    from translatedub.core.providers import asr, translate
    monkeypatch.setattr(asr.REGISTRY["whisper"], "is_available", lambda cfg: (True, ""))
    monkeypatch.setattr(translate.REGISTRY["google_free"], "is_available",
                        lambda cfg: (True, ""))
    resp = client.post("/api/config", json={"target_lang": "en", "asr_engine": "whisper"})
    assert resp.status_code == 200
    body = resp.json()["config"]
    assert body["has_gemini_key"] is False
    assert body["asr_engine"] == "whisper"


def test_post_config_saves_key_and_settings(client):
    resp = client.post("/api/config", json={"gemini_key": "k123", "target_lang": "en"})
    assert resp.status_code == 200
    body = resp.json()["config"]
    assert body["has_gemini_key"] is True
    assert body["target_lang"] == "en"
    # secret is stored but never returned
    assert "k123" not in resp.text
    assert config.get_secret("gemini_key") == "k123"


def test_reveal_missing_file(client):
    resp = client.post("/api/reveal", json={"path": "/no/such/file.mp4"})
    assert resp.json()["ok"] is False
