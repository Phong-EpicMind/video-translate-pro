"""Concrete ASR (speech-to-text) providers and the engine registry.

Free stack: faster-whisper (local, MIT), in the ``[free]`` extra. Premium: Gemini
(transcribe-only). Resolution ``"auto"`` prefers Gemini when a key is present, else
faster-whisper, else raises with guidance.
"""
from __future__ import annotations

from ..subtitles import Subtitle
from .base import ProviderUnavailable

# Cache one loaded WhisperModel per size (loading weights is expensive).
_WHISPER_CACHE: dict = {}


def _whisper_model(size: str):
    if size not in _WHISPER_CACHE:
        from faster_whisper import WhisperModel

        _WHISPER_CACHE[size] = WhisperModel(size, device="cpu", compute_type="int8")
    return _WHISPER_CACHE[size]


class WhisperProvider:
    name = "whisper"
    premium = False

    def __init__(self):
        self._model_size = "small"

    def is_available(self, config: dict) -> "tuple[bool, str]":
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            return False, "faster-whisper not installed — pip install translatedub[free]"
        return True, ""

    def transcribe(self, audio_path: str, src_lang: str, log=None) -> list:
        size = self._model_size or "small"
        model = _whisper_model(size)
        language = None if not src_lang or src_lang == "auto" else src_lang
        if log:
            log(f"Transcribing locally with faster-whisper ({size})...")
        segments, _info = model.transcribe(audio_path, language=language)
        subs: list = []
        for seg in segments:
            text = (seg.text or "").strip()
            if not text:
                continue
            subs.append(Subtitle(
                index=len(subs) + 1,
                start_ms=int(seg.start * 1000),
                end_ms=int(seg.end * 1000),
                original_text=text,
                translated_text="",
            ))
        return subs


class GeminiASRProvider:
    name = "gemini"
    premium = True

    def __init__(self):
        self._key = ""

    def is_available(self, config: dict) -> "tuple[bool, str]":
        if not config.get("gemini_key"):
            return False, "Gemini API key missing"
        return True, ""

    def transcribe(self, audio_path: str, src_lang: str, log=None) -> list:
        from ..transcribe import transcribe_only

        return transcribe_only(audio_path, self._key, src_lang, log)


REGISTRY: dict = {p.name: p for p in (WhisperProvider(), GeminiASRProvider())}


def get_asr_provider(name: str):
    try:
        return REGISTRY[name]
    except KeyError:
        raise ProviderUnavailable(f"Unknown ASR engine: {name}")


def resolve_asr_provider(name: str, config: dict, log=None):
    """Resolve an ASR engine. ``auto`` prefers Gemini (key) then whisper."""
    if name == "auto":
        if config.get("gemini_key"):
            name = "gemini"
        elif REGISTRY["whisper"].is_available(config)[0]:
            name = "whisper"
        else:
            raise ProviderUnavailable(
                "No ASR engine available — add a Gemini key or "
                "pip install translatedub[free]"
            )
    provider = get_asr_provider(name)
    ok, reason = provider.is_available(config)
    if not ok:
        raise ProviderUnavailable(f"{name} unavailable: {reason}")
    _bind(provider, config)
    return provider


def _bind(provider, config: dict) -> None:
    """Inject resolution inputs the pure protocol methods need at call time."""
    if isinstance(provider, GeminiASRProvider):
        provider._key = config.get("gemini_key", "")  # noqa: SLF001
    elif isinstance(provider, WhisperProvider):
        provider._model_size = config.get("whisper_model") or "small"  # noqa: SLF001


def available_asr_engines(config: "dict | None" = None) -> "list[dict]":
    cfg = config or {}
    out = []
    for name, provider in REGISTRY.items():
        ok, reason = provider.is_available(cfg)
        out.append({"name": name, "available": ok,
                    "premium": provider.premium, "reason": reason})
    return out
