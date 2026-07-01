"""Concrete translation providers and the engine registry.

Free: deep-translator (Google free, Apache-2.0), in the ``[free]`` extra. Premium: Gemini.
Resolution ``"auto"`` prefers Gemini when a key is present, else deep-translator, else
raises with guidance.
"""
from __future__ import annotations

from .base import ProviderUnavailable


class GoogleFreeProvider:
    name = "google_free"
    premium = False

    def is_available(self, config: dict) -> "tuple[bool, str]":
        try:
            import deep_translator  # noqa: F401
        except ImportError:
            return False, "deep-translator not installed — pip install translatedub[free]"
        return True, ""

    def translate(self, subtitles: list, src_lang: str, target_lang: str, log=None) -> list:
        from deep_translator import GoogleTranslator

        source = "auto" if not src_lang or src_lang == "auto" else src_lang
        translator = GoogleTranslator(source=source, target=target_lang)
        if log:
            log(f"Translating {len(subtitles)} lines with Google (free)...")
        for sub in subtitles:
            text = (sub.original_text or "").strip()
            if not text:
                continue
            try:
                sub.translated_text = (translator.translate(text) or "").strip()
            except Exception as exc:  # noqa: BLE001 - keep original on a per-line failure
                sub.translated_text = text
                if log:
                    log(f"Translate failed for '{text[:15]}...': {exc}")
        return subtitles


class GeminiTranslateProvider:
    name = "gemini"
    premium = True

    def __init__(self):
        self._key = ""

    def is_available(self, config: dict) -> "tuple[bool, str]":
        if not config.get("gemini_key"):
            return False, "Gemini API key missing"
        return True, ""

    def translate(self, subtitles: list, src_lang: str, target_lang: str, log=None) -> list:
        from ..transcribe import translate_texts

        texts = [(s.original_text or "").strip() for s in subtitles]
        translated = translate_texts(texts, self._key, src_lang, target_lang, log)
        for sub, value in zip(subtitles, translated):
            sub.translated_text = (value or "").strip()
        return subtitles


REGISTRY: dict = {p.name: p for p in (GoogleFreeProvider(), GeminiTranslateProvider())}


def get_translate_provider(name: str):
    try:
        return REGISTRY[name]
    except KeyError:
        raise ProviderUnavailable(f"Unknown translate engine: {name}")


def resolve_translate_provider(name: str, config: dict, log=None):
    """Resolve a translate engine. ``auto`` prefers Gemini (key) then google_free."""
    if name == "auto":
        if config.get("gemini_key"):
            name = "gemini"
        elif REGISTRY["google_free"].is_available(config)[0]:
            name = "google_free"
        else:
            raise ProviderUnavailable(
                "No translate engine available — add a Gemini key or "
                "pip install translatedub[free]"
            )
    provider = get_translate_provider(name)
    ok, reason = provider.is_available(config)
    if not ok:
        raise ProviderUnavailable(f"{name} unavailable: {reason}")
    if isinstance(provider, GeminiTranslateProvider):
        provider._key = config.get("gemini_key", "")  # noqa: SLF001
    return provider


def available_translate_engines(config: "dict | None" = None) -> "list[dict]":
    cfg = config or {}
    out = []
    for name, provider in REGISTRY.items():
        ok, reason = provider.is_available(cfg)
        out.append({"name": name, "available": ok,
                    "premium": provider.premium, "reason": reason})
    return out
