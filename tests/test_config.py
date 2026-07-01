import json
import os
import stat

import pytest

from translatedub import config


def test_defaults_when_empty(isolated_home):
    pub = config.public_config()
    assert pub["src_lang"] == "auto"
    assert pub["target_lang"] == "vi"
    assert pub["has_gemini_key"] is False
    assert pub["has_google_cloud_credentials"] is False


def test_set_and_get_secret(isolated_home):
    config.set_secret("gemini_key", "abc123")
    assert config.get_secret("gemini_key") == "abc123"
    assert config.has_secret("gemini_key") is True


def test_env_overrides_file(isolated_home, monkeypatch):
    config.set_secret("gemini_key", "from-file")
    monkeypatch.setenv("GEMINI_API_KEY", "from-env")
    assert config.get_secret("gemini_key") == "from-env"


def test_translatedub_env_takes_priority(isolated_home, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "legacy")
    monkeypatch.setenv("TRANSLATEDUB_GEMINI_KEY", "preferred")
    assert config.get_secret("gemini_key") == "preferred"


def test_google_application_credentials_file(isolated_home, tmp_path, monkeypatch):
    creds = tmp_path / "sa.json"
    creds.write_text('{"type": "service_account"}', encoding="utf-8")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(creds))
    assert "service_account" in config.get_secret("google_cloud_credentials")


def test_public_config_never_leaks_secret(isolated_home):
    config.set_secret("gemini_key", "topsecret")
    pub = config.public_config()
    assert "topsecret" not in json.dumps(pub)
    assert pub["has_gemini_key"] is True


def test_update_settings_ignores_unknown_and_persists(isolated_home):
    config.update_settings({"target_lang": "en", "bogus": "x"})
    data = config.load_config()
    assert data["target_lang"] == "en"
    assert "bogus" not in data


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits do not apply on Windows")
def test_config_file_permissions(isolated_home):
    config.set_secret("gemini_key", "abc")
    mode = stat.S_IMODE(os.stat(config.config_file()).st_mode)
    assert mode == 0o600


def test_get_secret_rejects_unknown_key(isolated_home):
    with pytest.raises(KeyError):
        config.get_secret("not_a_secret")


def test_default_tts_engine_is_edge():
    assert config.DEFAULT_SETTINGS["tts_engine"] == "edge"


def test_default_asr_translate_engines_are_auto():
    assert config.DEFAULT_SETTINGS["asr_engine"] == "auto"
    assert config.DEFAULT_SETTINGS["translate_engine"] == "auto"
    assert config.DEFAULT_SETTINGS["whisper_model"] == "small"


def test_public_config_lists_asr_and_translate_engines(isolated_home):
    pub = config.public_config()
    assert {e["name"] for e in pub["asr_engines"]} == {"whisper", "gemini"}
    assert {e["name"] for e in pub["translate_engines"]} == {"google_free", "gemini"}


def test_public_config_lists_engines_without_secrets(isolated_home):
    config.set_secret("gemini_key", "topsecret")
    pub = config.public_config()
    names = {e["name"] for e in pub["tts_engines"]}
    assert {"gtts", "edge", "google_cloud"} <= names
    assert "gemini_key" not in pub
    assert "google_cloud_credentials" not in pub
    assert "topsecret" not in json.dumps(pub)
    for e in pub["tts_engines"]:
        assert set(e) == {"name", "available", "premium", "reason"}
