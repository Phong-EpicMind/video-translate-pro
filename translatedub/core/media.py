"""ffmpeg-backed media operations: audio extraction, probing, muxing, subtitles.

Works with or without ``ffprobe``: when ffprobe is unavailable, duration and
audio-stream presence are parsed from ``ffmpeg -i`` stderr.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import uuid
from typing import Callable

from ..ffmpeg import ffmpeg_path, ffprobe_path

LogCallback = Callable[[str], None]


def _run(cmd: list[str], log: LogCallback | None = None) -> subprocess.CompletedProcess:
    if log:
        log(f"$ {' '.join(cmd)}")
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)")


def _duration_from_ffmpeg_stderr(stderr: str) -> float:
    match = _DURATION_RE.search(stderr)
    if not match:
        return 0.0
    h, m, s, cs = (int(g) for g in match.groups())
    return h * 3600 + m * 60 + s + cs / (10 ** len(match.group(4)))


def get_duration(path: str) -> float:
    """Return media duration in seconds (0.0 if it cannot be determined)."""
    probe = ffprobe_path()
    if probe:
        result = _run(
            [
                probe, "-v", "error", "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1", path,
            ]
        )
        try:
            return float(result.stdout.strip())
        except (ValueError, AttributeError):
            pass
    # Fallback: parse ffmpeg -i output.
    result = _run([ffmpeg_path(), "-hide_banner", "-i", path])
    return _duration_from_ffmpeg_stderr(result.stderr or "")


def has_audio_stream(path: str) -> bool:
    """Return True if the file has at least one audio stream."""
    probe = ffprobe_path()
    if probe:
        result = _run(
            [
                probe, "-v", "error", "-select_streams", "a",
                "-show_entries", "stream=codec_type", "-of", "default=nw=1:nk=1", path,
            ]
        )
        return bool((result.stdout or "").strip())
    result = _run([ffmpeg_path(), "-hide_banner", "-i", path])
    return bool(re.search(r"Stream #\d+:\d+.*: Audio:", result.stderr or ""))


def extract_audio(video_path: str, audio_path: str, log: LogCallback | None = None) -> bool:
    """Extract a mono mp3 audio track from a video."""
    result = _run(
        [
            ffmpeg_path(), "-y", "-i", video_path,
            "-vn", "-acodec", "libmp3lame", "-q:a", "2", "-ac", "1", audio_path,
        ],
        log,
    )
    if result.returncode != 0:
        if log:
            log(f"ffmpeg error: {result.stderr}")
        return False
    return True


def slice_audio(audio_path: str, start_sec: float, duration_sec: float, out_path: str,
                log: LogCallback | None = None) -> bool:
    """Cut a chunk of audio. Re-encodes for accurate seek boundaries."""
    result = _run(
        [
            ffmpeg_path(), "-y", "-ss", f"{start_sec}", "-t", f"{duration_sec}",
            "-i", audio_path, "-acodec", "libmp3lame", "-q:a", "2", out_path,
        ],
        log,
    )
    return result.returncode == 0 and os.path.exists(out_path)


def change_tempo(audio_path: str, tempo: float, log: LogCallback | None = None) -> bool:
    """Speed up / slow down audio in place using the atempo filter."""
    tempo = max(0.5, min(2.0, tempo))
    tmp = f"{os.path.splitext(audio_path)[0]}_t{uuid.uuid4().hex[:6]}.mp3"
    result = _run(
        [ffmpeg_path(), "-y", "-i", audio_path, "-filter:a", f"atempo={tempo:.3f}", tmp],
        log,
    )
    if result.returncode == 0 and os.path.exists(tmp):
        os.replace(tmp, audio_path)
        return True
    if os.path.exists(tmp):
        os.remove(tmp)
    return False


def _with_burn_ready_srt(srt_path: str):
    """Copy the SRT to an ASCII-safe sibling name and return (dir, basename, cleanup).

    Running ffmpeg with cwd=dir and referencing the bare basename avoids the
    cross-platform filtergraph path-escaping problems (spaces, ``:`` on Windows,
    quotes, unicode) entirely.
    """
    directory = os.path.dirname(os.path.abspath(srt_path))
    basename = f"burn_{uuid.uuid4().hex[:10]}.srt"
    dest = os.path.join(directory, basename)
    shutil.copyfile(srt_path, dest)

    def cleanup() -> None:
        try:
            os.remove(dest)
        except OSError:
            pass

    return directory, basename, cleanup


def export_subtitled_video(video_path: str, srt_path: str, output_path: str,
                           burn_subtitles: bool = True,
                           log: LogCallback | None = None) -> bool:
    """Export the original video with translated subtitles (no dubbing)."""
    if burn_subtitles:
        directory, basename, cleanup = _with_burn_ready_srt(srt_path)
        try:
            result = subprocess.run(
                [
                    ffmpeg_path(), "-y", "-i", os.path.abspath(video_path),
                    "-vf", f"subtitles={basename}",
                    "-c:v", "libx264", "-preset", "fast", "-c:a", "copy",
                    os.path.abspath(output_path),
                ],
                cwd=directory,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
        finally:
            cleanup()
    else:
        result = _run(
            [
                ffmpeg_path(), "-y", "-i", video_path, "-i", srt_path,
                "-map", "0", "-map", "1:0", "-c", "copy", "-c:s", "mov_text",
                output_path,
            ],
            log,
        )
    if result.returncode != 0:
        if log:
            log(f"ffmpeg error: {result.stderr}")
        return False
    return True


def mux_dubbed_audio(video_path: str, dubbed_audio_path: str, output_path: str,
                     original_vol: float, dub_vol: float,
                     srt_path: str | None = None, burn_subtitles: bool = False,
                     log: LogCallback | None = None) -> bool:
    """Mix the dubbed track over the original video, optionally with subtitles."""
    has_audio = has_audio_stream(video_path)
    burn = bool(burn_subtitles and srt_path and os.path.exists(srt_path))
    soft = bool(srt_path and os.path.exists(srt_path) and not burn_subtitles)

    directory = basename = None

    def cleanup() -> None:
        return None

    if burn:
        directory, basename, cleanup = _with_burn_ready_srt(srt_path)

    cmd = [ffmpeg_path(), "-y", "-i", os.path.abspath(video_path) if burn else video_path]
    cmd += ["-i", os.path.abspath(dubbed_audio_path) if burn else dubbed_audio_path]
    if soft:
        cmd += ["-i", srt_path]

    if has_audio and original_vol > 0:
        cmd += [
            "-filter_complex",
            f"[0:a]volume={original_vol:.2f}[a0];[1:a]volume={dub_vol:.2f}[a1];"
            f"[a0][a1]amix=inputs=2:duration=first[aout]",
        ]
    else:
        cmd += ["-filter_complex", f"[1:a]volume={dub_vol:.2f}[aout]"]
    cmd += ["-map", "0:v", "-map", "[aout]"]

    if burn:
        cmd += ["-vf", f"subtitles={basename}", "-c:v", "libx264", "-preset", "fast"]
    elif soft:
        cmd += ["-map", "2:s?", "-c:v", "copy", "-c:s", "mov_text"]
    else:
        cmd += ["-c:v", "copy"]

    cmd += ["-c:a", "aac", os.path.abspath(output_path) if burn else output_path]

    try:
        if log:
            log(f"$ {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=directory if burn else None,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
    finally:
        cleanup()

    if result.returncode != 0:
        if log:
            log(f"ffmpeg error: {result.stderr}")
        return False
    return True
