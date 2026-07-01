import pytest


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    """Point config storage at a temp dir and clear credential env vars."""
    monkeypatch.setenv("TRANSLATEDUB_HOME", str(tmp_path / ".translatedub"))
    for var in (
        "TRANSLATEDUB_GEMINI_KEY",
        "GEMINI_API_KEY",
        "TRANSLATEDUB_GOOGLE_CLOUD_CREDENTIALS",
        "GOOGLE_APPLICATION_CREDENTIALS",
    ):
        monkeypatch.delenv(var, raising=False)
    return tmp_path
