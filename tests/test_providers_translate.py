import sys
import types

import pytest

from translatedub.core.providers import translate as tr
from translatedub.core.providers.base import ProviderUnavailable
from translatedub.core.subtitles import Subtitle


def _sub(idx, text):
    return Subtitle(index=idx, start_ms=0, end_ms=1000, original_text=text, translated_text="")


def _install_fake_deep_translator(monkeypatch, mapping, fail_on=None):
    class FakeTranslator:
        def __init__(self, source=None, target=None):
            self.source, self.target = source, target

        def translate(self, text):
            if fail_on and text == fail_on:
                raise RuntimeError("boom")
            return mapping.get(text, text.upper())

    mod = types.ModuleType("deep_translator")
    mod.GoogleTranslator = FakeTranslator
    monkeypatch.setitem(sys.modules, "deep_translator", mod)


def test_registry_and_flags():
    assert set(tr.REGISTRY) == {"google_free", "gemini"}
    assert tr.get_translate_provider("google_free").premium is False
    assert tr.get_translate_provider("gemini").premium is True


def test_unknown_engine_raises():
    with pytest.raises(ProviderUnavailable):
        tr.get_translate_provider("nope")


def test_google_free_fills_translations(monkeypatch):
    _install_fake_deep_translator(monkeypatch, {"hello": "xin chào", "bye": "tạm biệt"})
    subs = [_sub(1, "hello"), _sub(2, "bye")]
    out = tr.get_translate_provider("google_free").translate(subs, "en", "vi")
    assert [s.translated_text for s in out] == ["xin chào", "tạm biệt"]


def test_google_free_keeps_original_on_failure(monkeypatch):
    _install_fake_deep_translator(monkeypatch, {"ok": "rồi"}, fail_on="bad")
    subs = [_sub(1, "ok"), _sub(2, "bad")]
    logs = []
    out = tr.get_translate_provider("google_free").translate(subs, "en", "vi", logs.append)
    assert out[0].translated_text == "rồi"
    assert out[1].translated_text == "bad"  # original preserved
    assert any("failed" in m.lower() for m in logs)


def test_google_free_skips_empty(monkeypatch):
    _install_fake_deep_translator(monkeypatch, {})
    subs = [_sub(1, "   ")]
    out = tr.get_translate_provider("google_free").translate(subs, "en", "vi")
    assert out[0].translated_text == ""


def test_gemini_translate_uses_translate_texts(monkeypatch):
    p = tr.get_translate_provider("gemini")
    p._key = "k"
    monkeypatch.setattr(
        "translatedub.core.transcribe.translate_texts",
        lambda texts, key, src, dst, log=None: [t.upper() for t in texts],
    )
    subs = [_sub(1, "a"), _sub(2, "b")]
    out = p.translate(subs, "en", "vi")
    assert [s.translated_text for s in out] == ["A", "B"]


def test_resolve_auto_prefers_gemini_with_key():
    p = tr.resolve_translate_provider("auto", {"gemini_key": "k"})
    assert p.name == "gemini" and p._key == "k"


def test_resolve_auto_uses_google_free_without_key(monkeypatch):
    monkeypatch.setattr(tr.REGISTRY["google_free"], "is_available", lambda cfg: (True, ""))
    p = tr.resolve_translate_provider("auto", {"gemini_key": ""})
    assert p.name == "google_free"


def test_resolve_auto_none_available_raises(monkeypatch):
    monkeypatch.setattr(tr.REGISTRY["google_free"], "is_available",
                        lambda cfg: (False, "nope"))
    with pytest.raises(ProviderUnavailable):
        tr.resolve_translate_provider("auto", {"gemini_key": ""})


def test_resolve_explicit_unavailable_raises():
    with pytest.raises(ProviderUnavailable):
        tr.resolve_translate_provider("gemini", {"gemini_key": ""})
