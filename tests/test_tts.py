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
