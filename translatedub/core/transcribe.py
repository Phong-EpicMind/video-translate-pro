"""Gemini-based transcription and translation, with chunking and retries."""

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


def _build_schema():
    """Return the pydantic response schema google-genai expects (imported lazily)."""
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


def _is_transient(err: str) -> bool:
    err_l = err.lower()
    return any(
        marker in err
        for marker in ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED")
    ) or "quota" in err_l


def _translate_chunk(client, schema, audio_chunk_path: str, src_lang: str,
                     target_lang: str, offset_ms: int, chunk_index: int,
                     log: LogCallback | None) -> list[Subtitle]:
    from google.genai import types

    prompt = _PROMPT.format(src=src_lang, dst=target_lang)
    last_exc: Exception | None = None

    for model_name in MODELS:
        for attempt in range(MAX_RETRIES_PER_MODEL):
            audio_file = None
            try:
                if log:
                    log(f"Chunk {chunk_index} via {model_name} (try {attempt + 1})...")
                audio_file = client.files.upload(file=audio_chunk_path)
                response = client.models.generate_content(
                    model=model_name,
                    contents=[audio_file, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                        temperature=0.0,
                    ),
                )
                _safe_delete(client, audio_file)
                audio_file = None

                data = json.loads(response.text)
                subs: list[Subtitle] = []
                for raw in data.get("subtitles", []):
                    subs.append(
                        Subtitle(
                            index=len(subs) + 1,
                            start_ms=int(raw.get("start_ms", 0)) + offset_ms,
                            end_ms=int(raw.get("end_ms", 0)) + offset_ms,
                            original_text=(raw.get("original_text") or "").strip(),
                            translated_text=(raw.get("translated_text") or "").strip(),
                        )
                    )
                return subs
            except Exception as exc:  # noqa: BLE001 - surfaced after retries
                last_exc = exc
                _safe_delete(client, audio_file)
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

    raise last_exc or RuntimeError("Transcription failed for a chunk.")


def _safe_delete(client, audio_file) -> None:
    if not audio_file:
        return
    try:
        client.files.delete(name=audio_file.name)
    except Exception:  # noqa: BLE001 - best-effort cleanup
        pass


def transcribe_and_translate(audio_path: str, gemini_key: str, src_lang: str,
                             target_lang: str,
                             log: LogCallback | None = None) -> list[Subtitle]:
    """Transcribe and translate an audio file, chunking long inputs.

    Returns a globally re-indexed list of :class:`Subtitle`.
    """
    from google import genai

    client = genai.Client(api_key=gemini_key)
    schema = _build_schema()

    duration = get_duration(audio_path)
    if duration <= 0:
        if log:
            log("Could not determine audio duration.")
        return []
    if log:
        log(f"Audio duration: {duration:.2f}s")

    if duration <= CHUNK_LIMIT_SEC:
        return reindex(
            _translate_chunk(client, schema, audio_path, src_lang, target_lang, 0, 1, log)
        )

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
                _translate_chunk(
                    client, schema, chunk_path, src_lang, target_lang,
                    int(start_sec * 1000), i + 1, log,
                )
            )
        finally:
            try:
                os.remove(chunk_path)
            except OSError:
                pass

    return reindex(all_subs)
