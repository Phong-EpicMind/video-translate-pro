from translatedub import pipeline
from translatedub.core.subtitles import Subtitle


def _sub(idx, orig, trans=""):
    return Subtitle(index=idx, start_ms=0, end_ms=1000,
                    original_text=orig, translated_text=trans)


def test_both_gemini_uses_combined_call(monkeypatch):
    calls = {}

    def fake_combined(audio, key, src, dst, log=None):
        calls["combined"] = (audio, key, src, dst)
        return [_sub(1, "hi", "xin chào")]

    monkeypatch.setattr(pipeline, "transcribe_and_translate", fake_combined)
    # Force both stages to resolve to gemini via the key.
    out = pipeline.transcribe_translate("a.mp3", "en", "vi", gemini_key="k")
    assert calls["combined"] == ("a.mp3", "k", "en", "vi")
    assert out[0].translated_text == "xin chào"


def test_mixed_runs_asr_then_translate(monkeypatch):
    order = []

    class FakeASR:
        name = "whisper"

        def transcribe(self, audio, src, log=None):
            order.append("asr")
            return [_sub(1, "hello")]

    class FakeTranslate:
        name = "google_free"

        def translate(self, subs, src, dst, log=None):
            order.append("translate")
            for s in subs:
                s.translated_text = s.original_text.upper()
            return subs

    monkeypatch.setattr(pipeline, "resolve_asr_provider", lambda name, cfg, log: FakeASR())
    monkeypatch.setattr(pipeline, "resolve_translate_provider",
                        lambda name, cfg, log: FakeTranslate())
    # transcribe_and_translate must NOT be called on the mixed path.
    monkeypatch.setattr(pipeline, "transcribe_and_translate",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("combined used")))

    out = pipeline.transcribe_translate("a.mp3", "en", "vi", gemini_key="k",
                                        asr_engine="whisper", translate_engine="google_free")
    assert order == ["asr", "translate"]
    assert out[0].translated_text == "HELLO"


def test_empty_asr_returns_empty(monkeypatch):
    class FakeASR:
        name = "whisper"

        def transcribe(self, audio, src, log=None):
            return []

    class FakeTranslate:
        name = "google_free"

        def translate(self, subs, src, dst, log=None):
            raise AssertionError("translate should be skipped on empty ASR")

    monkeypatch.setattr(pipeline, "resolve_asr_provider", lambda name, cfg, log: FakeASR())
    monkeypatch.setattr(pipeline, "resolve_translate_provider",
                        lambda name, cfg, log: FakeTranslate())
    out = pipeline.transcribe_translate("a.mp3", "en", "vi", asr_engine="whisper",
                                        translate_engine="google_free")
    assert out == []
