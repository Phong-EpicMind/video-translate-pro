"""Gemini-based transcription and translation, with chunking and retries.

Exposes three entry points sharing one retry/model-fallback core:

- :func:`transcribe_and_translate` — audio → translated subtitles in one call
  (the cheapest path when Gemini does both stages).
- :func:`transcribe_only` — audio → subtitles with ``original_text`` only.
- :func:`translate_texts` — list of strings → translated strings.
"""

from __future__ import annotations

import json
import os
import time
from typing import Callable

from .media import get_duration, slice_audio
from .subtitles import Subtitle, reindex

LogCallback = Callable[[str], None]

CHUNK_LIMIT_SEC = 600.0
CHUNK_SIZE_SEC = 300.0
TEXT_BATCH = 80  # subtitle lines per translate-only Gemini call
MODELS = ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite")
MAX_RETRIES_PER_MODEL = 2

_PROMPT = """You are a professional audio transcriber and translator.
Task:
1. Transcribe the provided audio file precisely.
2. Translate the transcribed text from '{src}' to '{dst}'.
3. Break the audio into subtitle segments. Each segment should be a single sentence
   or coherent phrase, generally 1 to 7 seconds long.
4. For each segment, output start and end time in MILLISECONDS (integers) relative
   to the start of this clip.
5. Output strictly in the specified JSON schema.

Ensure timestamps are accurate and aligned with the actual speech.
"""

_TRANSCRIBE_PROMPT = """You are a professional audio transcriber.
Task:
1. Transcribe the provided audio file precisely in its original language ('{src}').
2. Break the audio into subtitle segments, each a single sentence or coherent phrase,
   generally 1 to 7 seconds long.
3. For each segment, output start and end time in MILLISECONDS (integers) relative to
   the start of this clip, and the transcribed text.
4. Output strictly in the specified JSON schema.

Ensure timestamps are accurate and aligned with the actual speech.
"""

_TRANSLATE_PROMPT = """You are a professional translator.
Translate each numbered line from '{src}' to '{dst}'. Preserve meaning and tone.
Return strictly the specified JSON schema: for each input index, the translated text.
Do not merge, split, reorder, or drop lines.

Lines:
{lines}
"""


def _build_schema():
    """Combined transcribe+translate response schema (google-genai, lazy import)."""
    from pydantic import BaseModel

    class SubtitleSegment(BaseModel):
        index: int
        start_ms: int
        end_ms: int
        original_text: str
        translated_text: str

    class SubtitleList(BaseModel):
        subtitles: list[SubtitleSegment]

    return SubtitleList


def _build_transcribe_schema():
    from pydantic import BaseModel

    class Segment(BaseModel):
        index: int
        start_ms: int
        end_ms: int
        original_text: str

    class SegmentList(BaseModel):
        subtitles: list[Segment]

    return SegmentList


def _build_translate_schema():
    from pydantic import BaseModel

    class Line(BaseModel):
        index: int
        translated_text: str

    class LineList(BaseModel):
        lines: list[Line]

    return LineList


def _is_transient(err: str) -> bool:
    err_l = err.lower()
    return any(
        marker in err
        for marker in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")
    ) or "quota" in err_l


def _generate(client, contents, schema, label: str, log: LogCallback | None) -> str:
    """Call Gemini with model fallback + transient-retry. Returns response JSON text."""
    from google.genai import types

    last_exc: Exception | None = None
    for model_name in MODELS:
        for attempt in range(MAX_RETRIES_PER_MODEL):
            try:
                if log:
                    log(f"{label} via {model_name} (try {attempt + 1})...")
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                        temperature=0.0,
                    ),
                )
                return response.text
            except Exception as exc:  # noqa: BLE001 - surfaced after retries
                last_exc = exc
                err = str(exc)
                if _is_transient(err):
                    wait = 3 * (attempt + 1)
                    if log:
                        log(f"Server busy on {model_name}, retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    if log:
                        log(f"{model_name} failed: {err[:120]}")
                    break  # try next model
    raise last_exc or RuntimeError(f"{label} failed.")


def _safe_delete(client, audio_file) -> None:
    if not audio_file:
        return
    try:
        client.files.delete(name=audio_file.name)
    except Exception:  # noqa: BLE001 - best-effort cleanup
        pass


def _audio_chunk(client, schema, prompt: str, audio_chunk_path: str, offset_ms: int,
                 chunk_index: int, both: bool, log: LogCallback | None) -> list[Subtitle]:
    """Upload one audio chunk and parse subtitle segments from Gemini."""
    audio_file = None
    try:
        audio_file = client.files.upload(file=audio_chunk_path)
        text = _generate(client, [audio_file, prompt], schema,
                         f"Chunk {chunk_index}", log)
    finally:
        _safe_delete(client, audio_file)

    data = json.loads(text)
    subs: list[Subtitle] = []
    for raw in data.get("subtitles", []):
        subs.append(
            Subtitle(
                index=len(subs) + 1,
                start_ms=int(raw.get("start_ms", 0)) + offset_ms,
                end_ms=int(raw.get("end_ms", 0)) + offset_ms,
                original_text=(raw.get("original_text") or "").strip(),
                translated_text=(raw.get("translated_text") or "").strip() if both else "",
            )
        )
    return subs


def _run_audio_pipeline(audio_path: str, gemini_key: str, prompt: str, schema, both: bool,
                        log: LogCallback | None) -> list[Subtitle]:
    """Shared audio chunking for combined and transcribe-only Gemini paths."""
    from google import genai

    client = genai.Client(api_key=gemini_key)

    duration = get_duration(audio_path)
    if duration <= 0:
        if log:
            log("Could not determine audio duration.")
        return []
    if log:
        log(f"Audio duration: {duration:.2f}s")

    if duration <= CHUNK_LIMIT_SEC:
        return reindex(_audio_chunk(client, schema, prompt, audio_path, 0, 1, both, log))

    num_chunks = int(duration // CHUNK_SIZE_SEC) + (1 if duration % CHUNK_SIZE_SEC else 0)
    if log:
        log(f"Long audio ({duration:.0f}s); splitting into {num_chunks} chunks.")

    all_subs: list[Subtitle] = []
    for i in range(num_chunks):
        start_sec = i * CHUNK_SIZE_SEC
        chunk_path = f"{os.path.splitext(audio_path)[0]}_chunk_{i}.mp3"
        if log:
            log(f"Cutting chunk {i + 1}/{num_chunks} (from {start_sec:.0f}s)...")
        if not slice_audio(audio_path, start_sec, CHUNK_SIZE_SEC, chunk_path, log):
            if log:
                log(f"Failed to cut chunk {i + 1}; skipping.")
            continue
        try:
            all_subs.extend(
                _audio_chunk(client, schema, prompt, chunk_path,
                             int(start_sec * 1000), i + 1, both, log)
            )
        finally:
            try:
                os.remove(chunk_path)
            except OSError:
                pass
    return reindex(all_subs)


def transcribe_and_translate(audio_path: str, gemini_key: str, src_lang: str,
                             target_lang: str,
                             log: LogCallback | None = None) -> list[Subtitle]:
    """Transcribe and translate an audio file in one Gemini call, chunking long inputs."""
    prompt = _PROMPT.format(src=src_lang, dst=target_lang)
    return _run_audio_pipeline(audio_path, gemini_key, prompt, _build_schema(), True, log)


def transcribe_only(audio_path: str, gemini_key: str, src_lang: str,
                    log: LogCallback | None = None) -> list[Subtitle]:
    """Transcribe an audio file with Gemini (original text only)."""
    prompt = _TRANSCRIBE_PROMPT.format(src=src_lang)
    return _run_audio_pipeline(
        audio_path, gemini_key, prompt, _build_transcribe_schema(), False, log
    )


def translate_texts(texts: list, gemini_key: str, src_lang: str, target_lang: str,
                    log: LogCallback | None = None) -> list:
    """Translate a list of strings with Gemini, preserving order and length."""
    from google import genai

    if not texts:
        return []
    client = genai.Client(api_key=gemini_key)
    schema = _build_translate_schema()
    out = list(texts)  # default to originals; overwrite as translations arrive

    for start in range(0, len(texts), TEXT_BATCH):
        batch = texts[start:start + TEXT_BATCH]
        numbered = "\n".join(f"{i}. {t}" for i, t in enumerate(batch))
        prompt = _TRANSLATE_PROMPT.format(src=src_lang, dst=target_lang, lines=numbered)
        text = _generate(client, [prompt], schema,
                         f"Translate {start + 1}-{start + len(batch)}", log)
        data = json.loads(text)
        for line in data.get("lines", []):
            idx = int(line.get("index", -1))
            if 0 <= idx < len(batch):
                out[start + idx] = (line.get("translated_text") or "").strip()
    return out
