import sys
import types

import pytest

from translatedub.core.providers import asr
from translatedub.core.providers.base import ProviderUnavailable


class _Seg:
    def __init__(self, start, end, text):
        self.start, self.end, self.text = start, end, text


def _install_fake_whisper(monkeypatch, segments, calls):
    """Install a fake faster_whisper module whose model yields the given segments."""
    class FakeModel:
        def __init__(self, size, device=None, compute_type=None):
            calls.append(("init", size))

        def transcribe(self, audio_path, language=None):
            calls.append(("transcribe", audio_path, language))
            return iter(segments), object()

    mod = types.ModuleType("faster_whisper")
    mod.WhisperModel = FakeModel
    monkeypatch.setitem(sys.modules, "faster_whisper", mod)
    asr._WHISPER_CACHE.clear()


def test_registry_and_flags():
    assert set(asr.REGISTRY) == {"whisper", "gemini"}
    assert asr.get_asr_provider("whisper").premium is False
    assert asr.get_asr_provider("gemini").premium is True


def test_unknown_engine_raises():
    with pytest.raises(ProviderUnavailable):
        asr.get_asr_provider("nope")


def test_whisper_builds_subtitles(monkeypatch):
    calls = []
    _install_fake_whisper(monkeypatch, [_Seg(0.0, 1.5, " Hello "), _Seg(1.5, 3.0, "world")],
                          calls)
    p = asr.get_asr_provider("whisper")
    p._model_size = "small"
    subs = p.transcribe("a.mp3", "auto")
    assert [s.original_text for s in subs] == ["Hello", "world"]
    assert subs[0].start_ms == 0 and subs[0].end_ms == 1500
    assert subs[1].start_ms == 1500 and subs[1].end_ms == 3000
    assert all(s.translated_text == "" for s in subs)


def test_whisper_model_cached_across_calls(monkeypatch):
    calls = []
    _install_fake_whisper(monkeypatch, [_Seg(0.0, 1.0, "x")], calls)
    p = asr.get_asr_provider("whisper")
    p.transcribe("a.mp3", "auto")
    p.transcribe("b.mp3", "auto")
    inits = [c for c in calls if c[0] == "init"]
    assert len(inits) == 1  # model constructed once, reused


def test_whisper_passes_explicit_language(monkeypatch):
    calls = []
    _install_fake_whisper(monkeypatch, [_Seg(0.0, 1.0, "hola")], calls)
    asr.get_asr_provider("whisper").transcribe("a.mp3", "es")
    tr = [c for c in calls if c[0] == "transcribe"][0]
    assert tr[2] == "es"  # 'auto' -> None, explicit -> passed through


def test_resolve_auto_prefers_gemini_with_key():
    p = asr.resolve_asr_provider("auto", {"gemini_key": "k"})
    assert p.name == "gemini" and p._key == "k"


def test_resolve_auto_uses_whisper_without_key(monkeypatch):
    monkeypatch.setattr(asr.REGISTRY["whisper"], "is_available", lambda cfg: (True, ""))
    p = asr.resolve_asr_provider("auto", {"gemini_key": "", "whisper_model": "base"})
    assert p.name == "whisper" and p._model_size == "base"


def test_resolve_auto_none_available_raises(monkeypatch):
    monkeypatch.setattr(asr.REGISTRY["whisper"], "is_available",
                        lambda cfg: (False, "not installed"))
    with pytest.raises(ProviderUnavailable):
        asr.resolve_asr_provider("auto", {"gemini_key": ""})


def test_resolve_explicit_unavailable_raises():
    with pytest.raises(ProviderUnavailable):
        asr.resolve_asr_provider("gemini", {"gemini_key": ""})


def test_available_asr_engines_shape(monkeypatch):
    monkeypatch.setattr(asr.REGISTRY["whisper"], "is_available",
                        lambda cfg: (False, "not installed"))
    engines = asr.available_asr_engines({"gemini_key": ""})
    names = {e["name"] for e in engines}
    assert names == {"whisper", "gemini"}
    for e in engines:
        assert set(e) == {"name", "available", "premium", "reason"}
