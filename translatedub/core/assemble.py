"""Assemble per-segment TTS clips into a single dubbed audio track."""

from __future__ import annotations

from typing import Iterable

from ..ffmpeg import ffmpeg_path, ffprobe_path
from .subtitles import Subtitle


def assemble_dub_track(subtitles: Iterable[Subtitle], total_duration_ms: int,
                       output_path: str) -> None:
    """Overlay each subtitle's audio clip onto a silent track at its start time.

    Each subtitle must have ``audio_path`` set to an existing mp3 clip.
    """
    from pydub import AudioSegment

    AudioSegment.converter = ffmpeg_path()
    probe = ffprobe_path()
    if probe:
        AudioSegment.ffprobe = probe

    base = AudioSegment.silent(duration=max(0, total_duration_ms))
    for sub in subtitles:
        path = getattr(sub, "audio_path", None)
        if path:
            clip = AudioSegment.from_file(path, format="mp3")
            base = base.overlay(clip, position=max(0, sub.start_ms))
    base.export(output_path, format="mp3")
