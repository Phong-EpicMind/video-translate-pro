"""Assemble per-segment TTS clips into a single dubbed audio track."""

from __future__ import annotations

from typing import Iterable

from ..ffmpeg import ffmpeg_path, ffprobe_path
from .subtitles import Subtitle

OVERLAP_FADE_MS = 80  # short fade instead of an audible hard cut


def _clip_limit_ms(subtitles: list, i: int, total_ms: int) -> int:
    """Longest a clip may play without overlapping the next line's speech."""
    sub = subtitles[i]
    if i + 1 < len(subtitles):
        return max(0, subtitles[i + 1].start_ms - sub.start_ms)
    return max(0, total_ms - sub.start_ms)


def assemble_dub_track(subtitles: Iterable[Subtitle], total_duration_ms: int,
                       output_path: str) -> None:
    """Overlay each subtitle's audio clip onto a silent track at its start time.

    Each subtitle must have ``audio_path`` set to an existing mp3 clip. A clip
    that would run past the start of the next line is trimmed with a short
    fade — two lines must never talk over each other.
    """
    from pydub import AudioSegment

    AudioSegment.converter = ffmpeg_path()
    probe = ffprobe_path()
    if probe:
        AudioSegment.ffprobe = probe

    subs = list(subtitles)
    base = AudioSegment.silent(duration=max(0, total_duration_ms))
    for i, sub in enumerate(subs):
        path = getattr(sub, "audio_path", None)
        if not path:
            continue
        clip = AudioSegment.from_file(path, format="mp3")
        limit = _clip_limit_ms(subs, i, total_duration_ms)
        if limit and len(clip) > limit:
            clip = clip[:limit].fade_out(min(OVERLAP_FADE_MS, limit))
        base = base.overlay(clip, position=max(0, sub.start_ms))
    base.export(output_path, format="mp3")
