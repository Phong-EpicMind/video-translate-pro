"""Text-to-speech orchestration over pluggable engine providers.

Raw synthesis is delegated to a provider (see ``core/providers/tts.py``); this
module owns duration matching: fixed-rate engines (edge, gTTS) are corrected via
ffmpeg ``atempo``, native-rate engines (Google Cloud) re-synthesise at an
adjusted speaking rate.
"""

from __future__ import annotations

import os
from typing import Callable

from .media import change_tempo, get_duration
from .providers.tts import get_tts_provider, resolve_tts_provider

LogCallback = Callable[[str], None]

MIN_SPEED = 0.8
MAX_SPEED = 1.25
SPEED_TOLERANCE = 1.05  # only speed up when >5% over the target window


def _clamp(value: float, low: float = MIN_SPEED, high: float = MAX_SPEED) -> float:
    return max(low, min(high, value))


def _synthesize(provider, text, lang, output_path, voice_config, speed,
                log: LogCallback | None):
    """Synthesise with ``provider``; on a free-engine runtime failure fall back
    to gTTS (a deliberate premium engine still fails loudly). Returns the
    provider that actually produced the audio."""
    try:
        provider.synthesize(text, lang, output_path, voice_config, speed)
        return provider
    except Exception as exc:  # noqa: BLE001 - decide whether to degrade
        if provider.premium or provider.name == "gtts":
            raise
        fallback = get_tts_provider("gtts")
        if log:
            log(f"{provider.name} synthesis failed ({exc}); falling back to gtts.")
        fallback.synthesize(text, lang, output_path, voice_config, speed)
        return fallback


def synthesize_segment(text: str, lang: str, engine: str, output_path: str,
                       voice_config: dict | None = None,
                       target_duration_ms: int | None = None,
                       base_speed: float = 1.0, match_duration: bool = True,
                       log: LogCallback | None = None) -> bool:
    """Synthesise one subtitle segment to ``output_path``. Returns success."""
    voice_config = voice_config or {}
    try:
        provider = resolve_tts_provider(engine, voice_config, log)
        provider = _synthesize(provider, text, lang, output_path, voice_config,
                               base_speed, log)

        if not os.path.exists(output_path):
            return False

        actual_ms = int(get_duration(output_path) * 1000)

        if match_duration and target_duration_ms and target_duration_ms > 0:
            if actual_ms > target_duration_ms * SPEED_TOLERANCE:
                ratio = min(actual_ms / target_duration_ms, MAX_SPEED)
                if provider.supports_native_rate:
                    provider.synthesize(
                        text, lang, output_path, voice_config, _clamp(base_speed * ratio)
                    )
                else:
                    speed = _clamp(base_speed * ratio)
                    if abs(speed - 1.0) > 0.01:
                        change_tempo(output_path, speed, log)
        elif not provider.supports_native_rate and abs(base_speed - 1.0) > 0.01:
            change_tempo(output_path, _clamp(base_speed), log)

        return True
    except Exception as exc:  # noqa: BLE001 - reported to caller via log
        if log:
            log(f"TTS error for '{text[:15]}...': {exc}")
        return False
