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
    synthesize_segment,
    transcribe_and_translate,
    write_srt,
)

LogCallback = Callable[[str], None]


def translate_video(video_path: str, src_lang: str, target_lang: str,
                    gemini_key: str, log: LogCallback | None = None) -> list[Subtitle]:
    """Extract audio and produce translated subtitles for a video."""
    config.ensure_dirs()
    stem = os.path.splitext(os.path.basename(video_path))[0]
    audio_path = str(config.temp_dir() / f"{stem}_{uuid.uuid4().hex[:8]}.mp3")

    if log:
        log("Extracting audio...")
    if not extract_audio(video_path, audio_path, log):
        raise RuntimeError("Audio extraction failed.")

    if log:
        log("Transcribing and translating with Gemini...")
    subtitles = transcribe_and_translate(audio_path, gemini_key, src_lang, target_lang, log)
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
        for i, sub in enumerate(subtitles, start=1):
            clip = str(chunks_dir / f"segment_{sub.index}.mp3")
            if log:
                log(f"Synthesising line {i}/{len(subtitles)}...")
            ok = synthesize_segment(
                text=sub.translated_text, lang=target_lang, engine=engine,
                output_path=clip, voice_config=voice_config or {},
                target_duration_ms=sub.duration_ms, base_speed=base_speed,
                match_duration=match_duration, log=log,
            )
            if not ok:
                raise RuntimeError(f"TTS failed for line {sub.index}.")
            sub.audio_path = clip

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
