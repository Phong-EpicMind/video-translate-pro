"""Subtitle data model and SRT helpers.

Pure functions with no I/O beyond writing an SRT file. Fully unit-testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Subtitle:
    """A single subtitle segment.

    Times are in milliseconds relative to the start of the media.
    """

    index: int
    start_ms: int
    end_ms: int
    original_text: str = ""
    translated_text: str = ""
    audio_path: str | None = field(default=None)

    @property
    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)

    def to_dict(self) -> dict:
        data = {
            "index": self.index,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "original_text": self.original_text,
            "translated_text": self.translated_text,
        }
        if self.audio_path is not None:
            data["audio_path"] = self.audio_path
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Subtitle":
        return cls(
            index=int(data.get("index", 0)),
            start_ms=int(data.get("start_ms", 0)),
            end_ms=int(data.get("end_ms", 0)),
            original_text=(data.get("original_text") or "").strip(),
            translated_text=(data.get("translated_text") or "").strip(),
            audio_path=data.get("audio_path"),
        )


def ms_to_srt_time(ms: int) -> str:
    """Convert milliseconds to an SRT timestamp: ``HH:MM:SS,mmm``."""
    ms = max(0, int(ms))
    hours = ms // 3_600_000
    minutes = (ms % 3_600_000) // 60_000
    seconds = (ms % 60_000) // 1000
    milliseconds = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


_SRT_TIME_RE = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)")


def srt_time_to_ms(srt_time: str) -> int:
    """Convert an SRT timestamp (``HH:MM:SS,mmm``) to milliseconds.

    Accepts either a comma or a dot before the milliseconds. Returns 0 on no match.
    """
    match = _SRT_TIME_RE.match(srt_time.strip())
    if not match:
        return 0
    h, m, s, ms = (int(g) for g in match.groups())
    return h * 3_600_000 + m * 60_000 + s * 1000 + ms


def write_srt(subtitles: list[Subtitle], srt_path: str) -> None:
    """Write subtitles to a UTF-8 SRT file using the translated text."""
    with open(srt_path, "w", encoding="utf-8") as f:
        for sub in subtitles:
            f.write(
                f"{sub.index}\n"
                f"{ms_to_srt_time(sub.start_ms)} --> {ms_to_srt_time(sub.end_ms)}\n"
                f"{sub.translated_text}\n\n"
            )


def reindex(subtitles: list[Subtitle]) -> list[Subtitle]:
    """Renumber subtitles sequentially starting at 1 (in place) and return them."""
    for i, sub in enumerate(subtitles, start=1):
        sub.index = i
    return subtitles
