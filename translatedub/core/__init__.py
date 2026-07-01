"""TranslateDub core engine: web/CLI-agnostic translation and dubbing.

Public API:

- :class:`Subtitle`, SRT helpers (:func:`write_srt`, :func:`ms_to_srt_time`)
- :func:`transcribe_and_translate` — audio -> translated subtitles (Gemini)
- :func:`synthesize_segment` — text -> speech clip (gTTS / Google Cloud)
- :func:`assemble_dub_track` — segment clips -> single dubbed track
- media helpers: :func:`extract_audio`, :func:`get_duration`, :func:`mux_dubbed_audio`,
  :func:`export_subtitled_video`
"""

from .assemble import assemble_dub_track
from .media import (
    export_subtitled_video,
    extract_audio,
    get_duration,
    has_audio_stream,
    mux_dubbed_audio,
)
from .subtitles import Subtitle, ms_to_srt_time, reindex, srt_time_to_ms, write_srt
from .transcribe import transcribe_and_translate
from .tts import synthesize_segment

__all__ = [
    "Subtitle",
    "ms_to_srt_time",
    "srt_time_to_ms",
    "write_srt",
    "reindex",
    "extract_audio",
    "get_duration",
    "has_audio_stream",
    "mux_dubbed_audio",
    "export_subtitled_video",
    "transcribe_and_translate",
    "synthesize_segment",
    "assemble_dub_track",
]
