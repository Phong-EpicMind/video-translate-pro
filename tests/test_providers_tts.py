import sys

import pytest

from translatedub.core.providers.base import ProviderUnavailable
from translatedub.core.providers import tts as prov


# --- Registry -------------------------------------------------------------

def test_registry_has_expected_engines():
    assert set(prov.REGISTRY) == {"gtts", "edge", "google_cloud"}


def test_get_known_provider_returns_instance():
    p = prov.get_tts_provider("gtts")
    assert p.name == "gtts"
    assert p.premium is False
    assert p.supports_native_rate is False


def test_get_unknown_provider_raises():
    with pytest.raises(ProviderUnavailable):
        prov.get_tts_provider("nope")


def test_cloud_provider_flags():
    p = prov.get_tts_provider("google_cloud")
    assert p.premium is True
    assert p.supports_native_rate is True


def test_gtts_provider_synthesize_calls_gtts(monkeypatch, tmp_path):
    calls = {}

    class FakeGTTS:
        def __init__(self, text, lang):
            calls["text"], calls["lang"] = text, lang

        def save(self, path):
            calls["path"] = path
            open(path, "wb").close()

    monkeypatch.setitem(sys.modules, "gtts", type("m", (), {"gTTS": FakeGTTS}))
    out = str(tmp_path / "o.mp3")
    prov.get_tts_provider("gtts").synthesize("hi", "vi", out, {}, 1.0)
    assert calls == {"text": "hi", "lang": "vi", "path": out}


# --- edge-tts -------------------------------------------------------------

def test_edge_in_registry_and_flags():
    p = prov.get_tts_provider("edge")
    assert p.name == "edge" and p.premium is False
    assert p.supports_native_rate is False


def test_edge_default_voice_vietnamese():
    assert prov.get_tts_provider("edge").default_voice("vi") == "vi-VN-HoaiMyNeural"
    assert prov.get_tts_provider("edge").default_voice("en") == "en-US-AriaNeural"


def test_edge_unavailable_when_cli_missing(monkeypatch):
    monkeypatch.setattr(prov, "_edge_cli", lambda: None)
    ok, reason = prov.get_tts_provider("edge").is_available({})
    assert ok is False and "translatedub[free]" in reason


def test_edge_synthesize_invokes_cli(monkeypatch, tmp_path):
    monkeypatch.setattr(prov, "_edge_cli", lambda: "/usr/bin/edge-tts")
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        idx = cmd.index("--write-media") + 1
        with open(cmd[idx], "wb") as f:
            f.write(b"audio-bytes")
        return type("R", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr(prov.subprocess, "run", fake_run)
    out = str(tmp_path / "o.mp3")
    prov.get_tts_provider("edge").synthesize("xin chào", "vi", out, {}, 1.0)
    cmd = seen["cmd"]
    assert cmd[0] == "/usr/bin/edge-tts"
    assert "--voice" in cmd and "vi-VN-HoaiMyNeural" in cmd
    assert "--text" in cmd and "xin chào" in cmd
    assert cmd[cmd.index("--write-media") + 1] == out


def test_edge_synthesize_missing_output_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(prov, "_edge_cli", lambda: "/usr/bin/edge-tts")

    def fake_run(cmd, **kw):
        return type("R", (), {"returncode": 1, "stderr": "boom"})()  # no file written

    monkeypatch.setattr(prov.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError):
        prov.get_tts_provider("edge").synthesize("hi", "vi", str(tmp_path / "x.mp3"), {}, 1.0)


def test_edge_synthesize_empty_output_raises(monkeypatch, tmp_path):
    """Some builds exit 0 but write a 0-byte file on a 403; treat as failure."""
    monkeypatch.setattr(prov, "_edge_cli", lambda: "/usr/bin/edge-tts")

    def fake_run(cmd, **kw):
        idx = cmd.index("--write-media") + 1
        open(cmd[idx], "wb").close()  # exit 0 but empty file
        return type("R", (), {"returncode": 0, "stderr": "403 forbidden"})()

    monkeypatch.setattr(prov.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError):
        prov.get_tts_provider("edge").synthesize("hi", "vi", str(tmp_path / "x.mp3"), {}, 1.0)


# --- Resolution / fallback ------------------------------------------------

def test_resolve_free_falls_back_with_log(monkeypatch):
    monkeypatch.setattr(prov, "_edge_cli", lambda: None)  # edge unavailable
    logs = []
    p = prov.resolve_tts_provider("edge", {}, log=logs.append)
    assert p.name == "gtts"
    assert any("translatedub[free]" in m for m in logs)


def test_resolve_premium_missing_creds_raises():
    with pytest.raises(ProviderUnavailable):
        prov.resolve_tts_provider("google_cloud", {}, log=None)  # no credentials_json


def test_resolve_available_returns_same(monkeypatch):
    monkeypatch.setattr(prov, "_edge_cli", lambda: "/usr/bin/edge-tts")
    assert prov.resolve_tts_provider("edge", {}).name == "edge"


# --- Availability report --------------------------------------------------

def test_available_tts_engines_shape(monkeypatch):
    monkeypatch.setattr(prov, "_edge_cli", lambda: None)
    engines = prov.available_tts_engines({})
    edge = next(e for e in engines if e["name"] == "edge")
    assert edge["available"] is False and edge["premium"] is False
    assert "translatedub[free]" in edge["reason"]
