from translatedub.core import tts
from translatedub.core.providers import tts as prov


def _mock_gtts(monkeypatch, produced_ms):
    """Make gTTS synthesis a no-op file write and report a fixed duration."""
    def fake_synth(self, text, lang, output_path, voice_config, speaking_rate):
        with open(output_path, "wb") as f:
            f.write(b"fake")

    monkeypatch.setattr(prov.GTTSProvider, "synthesize", fake_synth)
    monkeypatch.setattr(tts, "get_duration", lambda path: produced_ms / 1000)


def test_clamp_bounds():
    assert tts._clamp(0.1) == tts.MIN_SPEED
    assert tts._clamp(9.0) == tts.MAX_SPEED
    assert tts._clamp(1.0) == 1.0


def test_gtts_no_speed_change_when_within_tolerance(monkeypatch, tmp_path):
    _mock_gtts(monkeypatch, produced_ms=1000)
    calls = []
    monkeypatch.setattr(tts, "change_tempo", lambda *a, **k: calls.append(a))
    out = str(tmp_path / "a.mp3")
    ok = tts.synthesize_segment("hi", "vi", "gtts", out, target_duration_ms=1000)
    assert ok is True
    assert calls == []  # 1000ms fits the 1000ms window (within tolerance)


def test_gtts_speeds_up_when_too_long(monkeypatch, tmp_path):
    _mock_gtts(monkeypatch, produced_ms=2000)  # twice the target window
    captured = {}

    def fake_tempo(path, tempo, log=None):
        captured["tempo"] = tempo
        return True

    monkeypatch.setattr(tts, "change_tempo", fake_tempo)
    out = str(tmp_path / "a.mp3")
    ok = tts.synthesize_segment("hi", "vi", "gtts", out, target_duration_ms=1000)
    assert ok is True
    # ratio would be 2.0 but is capped to MAX_SPEED
    assert captured["tempo"] == tts.MAX_SPEED


def test_unknown_engine_returns_false(tmp_path):
    out = str(tmp_path / "a.mp3")
    assert tts.synthesize_segment("hi", "vi", "nope", out) is False


def test_gtts_error_is_caught(monkeypatch, tmp_path):
    def boom(self, text, lang, output_path, voice_config, speaking_rate):
        raise RuntimeError("network down")

    monkeypatch.setattr(prov.GTTSProvider, "synthesize", boom)
    out = str(tmp_path / "a.mp3")
    assert tts.synthesize_segment("hi", "vi", "gtts", out) is False


def test_edge_runtime_failure_falls_back_to_gtts(monkeypatch, tmp_path):
    """A free engine failing mid-synthesis degrades to gTTS instead of hard-failing."""
    monkeypatch.setattr(prov, "_edge_cli", lambda: "/usr/bin/edge-tts")  # edge resolves

    def edge_boom(self, text, lang, output_path, voice_config, speaking_rate):
        raise RuntimeError("edge-tts failed: 403")

    def gtts_ok(self, text, lang, output_path, voice_config, speaking_rate):
        with open(output_path, "wb") as f:
            f.write(b"fake")

    monkeypatch.setattr(prov.EdgeTTSProvider, "synthesize", edge_boom)
    monkeypatch.setattr(prov.GTTSProvider, "synthesize", gtts_ok)
    monkeypatch.setattr(tts, "get_duration", lambda path: 1.0)
    logs = []
    out = str(tmp_path / "a.mp3")
    ok = tts.synthesize_segment("hi", "vi", "edge", out, target_duration_ms=1000,
                                log=logs.append)
    assert ok is True
    assert any("falling back to gtts" in m for m in logs)


def test_premium_runtime_failure_does_not_fall_back(monkeypatch, tmp_path):
    """A deliberate premium engine failing must not silently degrade."""
    def cloud_boom(self, text, lang, output_path, voice_config, speaking_rate):
        raise RuntimeError("cloud auth error")

    monkeypatch.setattr(prov.GoogleCloudProvider, "synthesize", cloud_boom)
    out = str(tmp_path / "a.mp3")
    vc = {"credentials_json": '{"type":"service_account"}'}
    # google_cloud is_available also imports the client; skip if the extra is absent.
    ok, _ = prov.GoogleCloudProvider().is_available(vc)
    if not ok:
        import pytest
        pytest.skip("google-cloud-texttospeech not installed")
    assert tts.synthesize_segment("hi", "vi", "google_cloud", out, voice_config=vc) is False
