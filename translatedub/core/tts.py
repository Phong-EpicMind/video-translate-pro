"""Text-to-speech orchestration over pluggable engine providers.

Raw synthesis is delegated to a provider (see ``core/providers/tts.py``); this
module owns duration matching: fixed-rate engines (edge, gTTS) are corrected via
ffmpeg ``atempo``, native-rate engines (Google Cloud) re-synthesise at an
adjusted speaking rate.
"""

from __future__ import annotations

import os
import time
from typing import Callable, Optional

from .media import change_tempo, get_duration
from .providers.tts import resolve_tts_provider

LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int, int, object], None]

MIN_SPEED = 0.8
MAX_SPEED = 1.25
SPEED_TOLERANCE = 1.05  # only speed up when >5% over the target window

# edge-tts is rate-limited by Microsoft and fails transiently (NoAudioReceived);
# measured live: retrying with a short backoff rescues the vast majority of lines.
TTS_MAX_ATTEMPTS = 3
RETRY_BACKOFF_S = 1.5

_sleep = time.sleep  # patchable in tests


def _clamp(value: float, low: float = MIN_SPEED, high: float = MAX_SPEED) -> float:
    return max(low, min(high, value))


def _synthesize(provider, text, lang, output_path, voice_config, speed,
                log: LogCallback | None):
    """Synthesise with ``provider``, retrying transient failures with backoff.

    Never switches provider: a mid-video engine swap would mix two voices in
    one output (job-level consistency lives in :func:`synthesize_segments`).
    Raises the last error when all attempts fail.
    """
    for attempt in range(1, TTS_MAX_ATTEMPTS + 1):
        try:
            provider.synthesize(text, lang, output_path, voice_config, speed)
            return provider
        except Exception as exc:  # noqa: BLE001 - retried, then reported
            if attempt == TTS_MAX_ATTEMPTS:
                raise
            if log:
                log(f"{provider.name} attempt {attempt} failed ({exc}); retrying...")
            _sleep(RETRY_BACKOFF_S * attempt)


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


def synthesize_segments(subtitles, lang: str, engine: str, chunks_dir: str,
                        voice_config: dict | None = None, base_speed: float = 1.0,
                        match_duration: bool = True,
                        log: LogCallback | None = None,
                        progress: Optional[ProgressCallback] = None) -> str:
    """Synthesise every subtitle into ``chunks_dir`` with ONE consistent voice.

    Sets ``sub.audio_path`` on each subtitle. If a free engine (e.g. edge) dies
    for good on any line despite retries, the ENTIRE job is re-synthesised with
    gTTS from line one — the output video must never mix two voices. Premium
    engines and gTTS itself fail loudly instead. Returns the engine actually
    used. Raises ``RuntimeError`` when no engine can complete the job.
    """
    voice_config = voice_config or {}
    resolved = resolve_tts_provider(engine, voice_config, log)

    def _run(engine_name: str) -> Optional[int]:
        """One full pass; returns the failing subtitle index or None."""
        subs = list(subtitles)
        for i, sub in enumerate(subs, start=1):
            clip = os.path.join(chunks_dir, f"segment_{sub.index}.mp3")
            if progress:
                progress(i, len(subs), sub)
            elif log:
                log(f"Synthesising line {i}/{len(subs)}...")
            ok = synthesize_segment(
                text=sub.translated_text, lang=lang, engine=engine_name,
                output_path=clip, voice_config=voice_config,
                target_duration_ms=sub.duration_ms, base_speed=base_speed,
                match_duration=match_duration, log=log,
            )
            if not ok:
                return sub.index
            sub.audio_path = clip
        return None

    failed = _run(resolved.name)
    if failed is None:
        return resolved.name

    if resolved.premium or resolved.name == "gtts":
        raise RuntimeError(f"TTS failed for line {failed}.")

    if log:
        log(f"{resolved.name} keeps failing (line {failed}); re-dubbing the whole "
            "video with gtts for voice consistency (one voice throughout).")
    failed = _run("gtts")
    if failed is not None:
        raise RuntimeError(f"TTS failed for line {failed}.")
    return "gtts"
