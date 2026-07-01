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
