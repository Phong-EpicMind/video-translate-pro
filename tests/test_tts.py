import pytest

from translatedub.core import tts
from translatedub.core.providers import tts as prov


@pytest.fixture(autouse=True)
def no_retry_sleep(monkeypatch):
    """Retry backoff must never make the unit suite actually sleep."""
    monkeypatch.setattr(tts, "_sleep", lambda s: None)


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
    # ratio would be 2.0 but is capped at the hard limit (chipmunk guard)
    assert captured["tempo"] == tts.MAX_FIT_SPEED


def test_speedup_beyond_comfort_only_when_needed_to_fit(monkeypatch, tmp_path):
    """1400ms into a 1000ms slot needs 1.4x: above the comfort cap (1.25) but
    within the hard cap (1.6). Compressing beats cutting the last words off."""
    _mock_gtts(monkeypatch, produced_ms=1400)
    captured = {}

    def fake_tempo(path, tempo, log=None):
        captured["tempo"] = tempo
        return True

    monkeypatch.setattr(tts, "change_tempo", fake_tempo)
    out = str(tmp_path / "a.mp3")
    ok = tts.synthesize_segment("hi", "vi", "gtts", out, target_duration_ms=1000)
    assert ok is True
    assert abs(captured["tempo"] - 1.4) < 0.01  # exactly what fits, no more


def test_unknown_engine_returns_false(tmp_path):
    out = str(tmp_path / "a.mp3")
    assert tts.synthesize_segment("hi", "vi", "nope", out) is False


def test_gtts_error_is_caught(monkeypatch, tmp_path):
    def boom(self, text, lang, output_path, voice_config, speaking_rate):
        raise RuntimeError("network down")

    monkeypatch.setattr(prov.GTTSProvider, "synthesize", boom)
    out = str(tmp_path / "a.mp3")
    assert tts.synthesize_segment("hi", "vi", "gtts", out) is False


def test_transient_edge_failure_is_retried(monkeypatch, tmp_path):
    """Transient failures (edge-tts rate limiting) are retried with backoff."""
    monkeypatch.setattr(prov, "_edge_cli", lambda: "/usr/bin/edge-tts")
    sleeps = []
    monkeypatch.setattr(tts, "_sleep", sleeps.append)
    attempts = {"n": 0}

    def flaky_edge(self, text, lang, output_path, voice_config, speaking_rate):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError("edge-tts failed: NoAudioReceived")
        with open(output_path, "wb") as f:
            f.write(b"fake")

    monkeypatch.setattr(prov.EdgeTTSProvider, "synthesize", flaky_edge)
    monkeypatch.setattr(tts, "get_duration", lambda path: 1.0)
    out = str(tmp_path / "a.mp3")
    ok = tts.synthesize_segment("hi", "vi", "edge", out, target_duration_ms=1000)
    assert ok is True
    assert attempts["n"] == 3
    assert len(sleeps) == 2  # waited before each retry


def test_edge_persistent_failure_does_NOT_switch_voice_mid_segment(monkeypatch, tmp_path):
    """No more silent per-segment gTTS fallback: it caused mixed voices in one video.
    A persistent edge failure fails the segment; voice consistency is handled at
    the job level (synthesize_segments)."""
    monkeypatch.setattr(prov, "_edge_cli", lambda: "/usr/bin/edge-tts")
    monkeypatch.setattr(tts, "_sleep", lambda s: None)

    def edge_boom(self, text, lang, output_path, voice_config, speaking_rate):
        raise RuntimeError("edge-tts failed: NoAudioReceived")

    gtts_calls = []

    def gtts_spy(self, text, lang, output_path, voice_config, speaking_rate):
        gtts_calls.append(text)

    monkeypatch.setattr(prov.EdgeTTSProvider, "synthesize", edge_boom)
    monkeypatch.setattr(prov.GTTSProvider, "synthesize", gtts_spy)
    out = str(tmp_path / "a.mp3")
    ok = tts.synthesize_segment("hi", "vi", "edge", out)
    assert ok is False
    assert gtts_calls == []  # the segment must NOT come out in a different voice


def _subs(n):
    from translatedub.core.subtitles import Subtitle
    return [Subtitle(index=i, start_ms=i * 1000, end_ms=i * 1000 + 900,
                     original_text=f"line {i}", translated_text=f"dòng {i}")
            for i in range(1, n + 1)]


def test_synthesize_segments_switches_whole_job_for_voice_consistency(monkeypatch, tmp_path):
    """If edge dies for good on one line, the ENTIRE video is re-dubbed with gTTS
    so the output never mixes two voices."""
    monkeypatch.setattr(prov, "_edge_cli", lambda: "/usr/bin/edge-tts")
    monkeypatch.setattr(tts, "_sleep", lambda s: None)
    monkeypatch.setattr(tts, "get_duration", lambda path: 0.9)
    edge_calls, gtts_calls = [], []

    def edge_synth(self, text, lang, output_path, voice_config, speaking_rate):
        if text == "dòng 2":
            raise RuntimeError("edge-tts failed: NoAudioReceived")
        edge_calls.append(text)
        with open(output_path, "wb") as f:
            f.write(b"edge")

    def gtts_synth(self, text, lang, output_path, voice_config, speaking_rate):
        gtts_calls.append(text)
        with open(output_path, "wb") as f:
            f.write(b"gtts")

    monkeypatch.setattr(prov.EdgeTTSProvider, "synthesize", edge_synth)
    monkeypatch.setattr(prov.GTTSProvider, "synthesize", gtts_synth)
    subs = _subs(3)
    logs = []
    used = tts.synthesize_segments(subs, "vi", "edge", str(tmp_path), log=logs.append)
    assert used == "gtts"
    # every line was re-synthesised with gTTS — one single voice
    assert gtts_calls == ["dòng 1", "dòng 2", "dòng 3"]
    for s in subs:
        with open(s.audio_path, "rb") as f:
            assert f.read() == b"gtts"
    assert any("voice consistency" in m for m in logs)


def test_synthesize_segments_keeps_edge_when_all_lines_succeed(monkeypatch, tmp_path):
    monkeypatch.setattr(prov, "_edge_cli", lambda: "/usr/bin/edge-tts")
    monkeypatch.setattr(tts, "get_duration", lambda path: 0.9)
    gtts_calls = []

    def edge_synth(self, text, lang, output_path, voice_config, speaking_rate):
        with open(output_path, "wb") as f:
            f.write(b"edge")

    monkeypatch.setattr(prov.EdgeTTSProvider, "synthesize", edge_synth)
    monkeypatch.setattr(
        prov.GTTSProvider, "synthesize",
        lambda self, *a, **k: gtts_calls.append(a),
    )
    subs = _subs(2)
    used = tts.synthesize_segments(subs, "vi", "edge", str(tmp_path))
    assert used == "edge"
    assert gtts_calls == []
    assert all(getattr(s, "audio_path", None) for s in subs)


def test_synthesize_segments_raises_when_gtts_also_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(tts, "_sleep", lambda s: None)

    def boom(self, text, lang, output_path, voice_config, speaking_rate):
        raise RuntimeError("network down")

    monkeypatch.setattr(prov.GTTSProvider, "synthesize", boom)
    import pytest
    with pytest.raises(RuntimeError):
        tts.synthesize_segments(_subs(1), "vi", "gtts", str(tmp_path))


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


def test_synthesize_segments_targets_gap_to_next_line(monkeypatch, tmp_path):
    """Duration matching must aim at the gap to the NEXT line, not the subtitle
    window: clips within the gap need no speed-up, and clips capped at max speed
    must not spill into the next line (that caused overlapping voices)."""
    monkeypatch.setattr(prov, "_edge_cli", lambda: "/usr/bin/edge-tts")
    targets = []

    def spy_segment(text, lang, engine, output_path, voice_config=None,
                    target_duration_ms=None, base_speed=1.0, match_duration=True,
                    log=None):
        targets.append(target_duration_ms)
        with open(output_path, "wb") as f:
            f.write(b"x")
        return True

    monkeypatch.setattr(tts, "synthesize_segment", spy_segment)
    from translatedub.core.subtitles import Subtitle
    subs = [
        Subtitle(index=1, start_ms=0, end_ms=900, original_text="a", translated_text="a"),
        Subtitle(index=2, start_ms=2000, end_ms=2500, original_text="b", translated_text="b"),
        Subtitle(index=3, start_ms=4000, end_ms=4800, original_text="c", translated_text="c"),
    ]
    tts.synthesize_segments(subs, "vi", "edge", str(tmp_path))
    # line 1 may run until line 2 starts (2000ms), line 2 until 4000-2000=2000ms;
    # the last line keeps its own subtitle window.
    assert targets == [2000, 2000, 800]
