"""High-level orchestration shared by the CLI and the web server.

Each function takes an optional ``log`` callback so callers can stream progress.
"""

from __future__ import annotations

import os
import shutil
import uuid
from typing import Callable

from . import config
from .core import (
    Subtitle,
    assemble_dub_track,
    export_subtitled_video,
    extract_audio,
    get_duration,
    mux_dubbed_audio,
    synthesize_segments,
    transcribe_and_translate,
    write_srt,
)
from .core.providers import resolve_asr_provider, resolve_translate_provider

LogCallback = Callable[[str], None]


def transcribe_translate(audio_path: str, src_lang: str, target_lang: str, *,
                         gemini_key: str = "", asr_engine: str = "auto",
                         translate_engine: str = "auto", whisper_model: str = "small",
                         log: LogCallback | None = None) -> list[Subtitle]:
    """Transcribe + translate an audio file via the resolved ASR/translate engines.

    When both stages resolve to Gemini, the single combined call is used (cheapest);
    otherwise ASR runs first, then translation.
    """
    cfg = {"gemini_key": gemini_key, "whisper_model": whisper_model}
    asr = resolve_asr_provider(asr_engine, cfg, log)
    translator = resolve_translate_provider(translate_engine, cfg, log)

    if asr.name == "gemini" and translator.name == "gemini":
        return transcribe_and_translate(audio_path, gemini_key, src_lang, target_lang, log)

    subtitles = asr.transcribe(audio_path, src_lang, log)
    if not subtitles:
        return []
    return translator.translate(subtitles, src_lang, target_lang, log)


def translate_video(video_path: str, src_lang: str, target_lang: str,
                    gemini_key: str = "", log: LogCallback | None = None, *,
                    asr_engine: str = "auto", translate_engine: str = "auto",
                    whisper_model: str = "small") -> list[Subtitle]:
    """Extract audio and produce translated subtitles for a video."""
    config.ensure_dirs()
    stem = os.path.splitext(os.path.basename(video_path))[0]
    audio_path = str(config.temp_dir() / f"{stem}_{uuid.uuid4().hex[:8]}.mp3")

    if log:
        log("Extracting audio...")
    if not extract_audio(video_path, audio_path, log):
        raise RuntimeError("Audio extraction failed.")

    try:
        subtitles = transcribe_translate(
            audio_path, src_lang, target_lang, gemini_key=gemini_key,
            asr_engine=asr_engine, translate_engine=translate_engine,
            whisper_model=whisper_model, log=log,
        )
    finally:
        try:
            os.remove(audio_path)
        except OSError:
            pass
    if not subtitles:
        raise RuntimeError("No subtitles were produced.")
    return subtitles


def export_video(video_path: str, subtitles: list[Subtitle], output_path: str,
                 *, mode: str = "dubbed", engine: str = "gtts",
                 target_lang: str = "vi", voice_config: dict | None = None,
                 base_speed: float = 1.0, match_duration: bool = True,
                 original_vol: float = 0.1, dub_vol: float = 1.0,
                 burn_subtitles: bool = False,
                 log: LogCallback | None = None) -> str:
    """Render the final video (dubbed or subtitles-only). Returns ``output_path``."""
    config.ensure_dirs()
    stem = os.path.splitext(os.path.basename(output_path))[0]
    srt_path = str(config.temp_dir() / f"{stem}_{uuid.uuid4().hex[:8]}.srt")
    write_srt(subtitles, srt_path)

    if mode == "subtitles_only":
        if log:
            log("Exporting subtitles-only video...")
        if not export_subtitled_video(video_path, srt_path, output_path, burn_subtitles, log):
            raise RuntimeError("Subtitle export failed.")
        return output_path

    chunks_dir = config.temp_dir() / f"chunks_{uuid.uuid4().hex}"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    dubbed_audio = str(config.temp_dir() / f"{stem}_{uuid.uuid4().hex[:8]}_dub.mp3")
    try:
        synthesize_segments(
            subtitles, lang=target_lang, engine=engine, chunks_dir=str(chunks_dir),
            voice_config=voice_config or {}, base_speed=base_speed,
            match_duration=match_duration, log=log,
        )

        if log:
            log("Assembling dubbed track...")
        total_ms = int(get_duration(video_path) * 1000)
        assemble_dub_track(subtitles, total_ms, dubbed_audio)

        if log:
            log("Muxing audio with video...")
        if not mux_dubbed_audio(
            video_path, dubbed_audio, output_path, original_vol, dub_vol,
            srt_path=srt_path, burn_subtitles=burn_subtitles, log=log,
        ):
            raise RuntimeError("Muxing failed.")
        return output_path
    finally:
        shutil.rmtree(chunks_dir, ignore_errors=True)
