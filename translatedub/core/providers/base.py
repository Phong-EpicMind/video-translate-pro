"""Provider contract shared by pluggable pipeline engines."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


class ProviderUnavailable(Exception):
    """A requested engine cannot run in the current environment."""


@runtime_checkable
class TTSProvider(Protocol):
    """One text-to-speech engine behind a common interface.

    ``supports_native_rate`` is True when the engine can synthesize at an
    adjusted speaking rate (Google Cloud); False when the rate is fixed and any
    duration correction must be applied post-hoc via ffmpeg ``atempo``.
    """

    name: str
    premium: bool
    supports_native_rate: bool

    def is_available(self, voice_config: dict) -> "tuple[bool, str]":
        """Return ``(available, reason)``; ``reason`` is a hint when unavailable."""
        ...

    def default_voice(self, lang: str) -> "str | None":
        """Return the default voice id for ``lang`` (or None)."""
        ...

    def synthesize(self, text: str, lang: str, output_path: str,
                   voice_config: dict, speaking_rate: float) -> None:
        """Synthesize one segment to ``output_path``; raise on failure."""
        ...


@runtime_checkable
class ASRProvider(Protocol):
    """One speech-to-text engine. ``config`` carries resolution inputs
    (``gemini_key``, ``whisper_model``)."""

    name: str
    premium: bool

    def is_available(self, config: dict) -> "tuple[bool, str]":
        ...

    def transcribe(self, audio_path: str, src_lang: str,
                   log=None) -> list:
        """Return subtitles with ``original_text`` filled (``translated_text`` empty)."""
        ...


@runtime_checkable
class TranslateProvider(Protocol):
    """One translation engine. ``config`` carries resolution inputs (``gemini_key``)."""

    name: str
    premium: bool

    def is_available(self, config: dict) -> "tuple[bool, str]":
        ...

    def translate(self, subtitles: list, src_lang: str, target_lang: str,
                  log=None) -> list:
        """Fill ``translated_text`` on each subtitle in place; return the list."""
        ...
