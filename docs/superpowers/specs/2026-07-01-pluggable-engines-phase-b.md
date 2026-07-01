# Pluggable engines — Phase B design (free ASR + translate)

**Date:** 2026-07-01
**Status:** Approved direction; spec for review before implementation
**Depends on:** Phase A (TTS provider seam, merged into `main` via PR #11)

## Goal

Split the transcription pipeline into two independently swappable stages — **ASR**
(speech → original text + timings) and **translate** (original → target text) — and add a
**zero-key free stack**: faster-whisper (local ASR) + deep-translator (Google free). After
this phase the *entire* pipeline can run with **no API key**.

Gemini keeps doing ASR+translate in a single call when both stages are Gemini (no cost or
latency regression for key users).

## Locked decisions (2026-07-01)

- **Default faster-whisper model: `small`** (~500MB, balanced on CPU). User-configurable.
- **Default engine preference: Gemini-first when a key is present**, otherwise the free
  local stack. So a key user's behavior is unchanged (Gemini combined call); a keyless user
  with `[free]` installed gets whisper + deep-translator automatically.

## Licensing (already verified in CLAUDE.md — all clean)

faster-whisper **MIT**, deep-translator **Apache-2.0**, Whisper weights **MIT**. All
permissive; added to the `[free]` extra. No new license risk.

## Architecture

Extend the Phase A provider pattern to two more stages.

### New protocols (`core/providers/base.py`)

- `ASRProvider`: `name`, `premium`, `is_available(config) -> (bool, str)`,
  `transcribe(audio_path, src_lang, log) -> list[Subtitle]` (fills `original_text`,
  leaves `translated_text` empty).
- `TranslateProvider`: `name`, `premium`, `is_available(config) -> (bool, str)`,
  `translate(subtitles, src_lang, target_lang, log) -> list[Subtitle]` (fills
  `translated_text` in place; returns the list).

`config` here is a plain dict carrying resolution inputs: `gemini_key`, `whisper_model`.
Providers never read `translatedub.config` directly (keeps `core` pure).

### ASR providers (`core/providers/asr.py`)

- `WhisperProvider` (`name="whisper"`, `premium=False`): faster-whisper, `[free]`.
  - `is_available`: True iff `faster_whisper` importable; else
    `"faster-whisper not installed — pip install translatedub[free]"`.
  - `transcribe`: load a cached `WhisperModel(model_size, device="cpu",
    compute_type="int8")` (model size from `config["whisper_model"]`, default `small`);
    `model.transcribe(audio_path, language=None if src=="auto" else src)`; build one
    `Subtitle` per segment (`start`/`end` seconds → ms, `original_text=seg.text.strip()`).
    Cache keyed by model size so repeated runs don't reload weights.
- `GeminiASRProvider` (`name="gemini"`, `premium=True`): transcribe-only Gemini call
  (reuses the chunking/retry machinery in `core/transcribe.py`); `is_available` requires
  `config["gemini_key"]`.

### Translate providers (`core/providers/translate.py`)

- `GoogleFreeProvider` (`name="google_free"`, `premium=False`): deep-translator, `[free]`.
  - `is_available`: True iff `deep_translator` importable.
  - `translate`: `GoogleTranslator(source=src or "auto", target=target)`; translate each
    subtitle's `original_text` (batched with `translate_batch`, guarding empty strings);
    on a per-item failure keep the original text and log. No key, online service.
- `GeminiTranslateProvider` (`name="gemini"`, `premium=True`): translate-only Gemini call
  over the collected texts (JSON in/out, chunked by count to stay within limits);
  `is_available` requires `config["gemini_key"]`.

### Registries & resolution

Mirror Phase A. In `asr.py` / `translate.py`:
`REGISTRY`, `get_*_provider`, `resolve_*_provider(name, config, log)`,
`available_*_engines(config)`.

Resolution for `name == "auto"`:
1. If `config["gemini_key"]` present → `gemini`.
2. Else if the free provider (`whisper` / `google_free`) is available → use it.
3. Else raise `ProviderUnavailable` with guidance ("add a Gemini key, or
   `pip install translatedub[free]`").

Explicit names resolve directly; an unavailable explicit choice raises (fail loud) —
consistent with Phase A. (ASR/translate have no always-present free fallback like gTTS, so
there is no silent free-to-free degrade here; "auto" already encodes the preference.)

### Combined Gemini fast-path

`core/transcribe.py` keeps `transcribe_and_translate` (one Gemini call). New pipeline
orchestration decides:

- If resolved ASR and translate are **both** `gemini` → call `transcribe_and_translate`
  (single combined call — unchanged behavior/cost for key users).
- Else → `asr.transcribe(...)` then `translate.translate(...)`.

### Shared pipeline entry point (`pipeline.py`)

Add one function both adapters call, so engine logic lives in exactly one place:

```python
def transcribe_translate(audio_path, src_lang, target_lang, *, gemini_key="",
                         asr_engine="auto", translate_engine="auto",
                         whisper_model="small", log=None) -> list[Subtitle]:
    cfg = {"gemini_key": gemini_key, "whisper_model": whisper_model}
    asr = resolve_asr_provider(asr_engine, cfg, log)
    tr = resolve_translate_provider(translate_engine, cfg, log)
    if asr.name == "gemini" and tr.name == "gemini":
        return transcribe_and_translate(audio_path, gemini_key, src_lang, target_lang, log)
    subs = asr.transcribe(audio_path, src_lang, log)
    return tr.translate(subs, src_lang, target_lang, log)
```

- `translate_video` (CLI path) extracts audio then delegates to `transcribe_translate`.
- `web/server.py` replaces its direct `transcribe_and_translate(...)` call (inside the SSE
  generator) with `transcribe_translate(...)`, passing the request's engine settings. The
  SSE step name stays `transcribe`; only the underlying call changes. Message text becomes
  engine-aware ("Nhận diện bằng <asr> · Dịch bằng <translate>...").

## Config, CLI, UI

- `config.DEFAULT_SETTINGS` gains `asr_engine="auto"`, `translate_engine="auto"`,
  `whisper_model="small"`. `public_config()` adds `asr_engines` and `translate_engines`
  availability lists (via `available_*_engines`, using the stored Gemini key presence — no
  secret values).
- CLI `translate` gains `--asr-engine {auto,whisper,gemini}`,
  `--translate-engine {auto,google_free,gemini}`, `--whisper-model {tiny,base,small,medium,large-v3}`.
- Web UI: two selectors (ASR, translate) plus a whisper-model selector shown when ASR is
  whisper/auto. Additive to the config payload; SSE/JSON contract otherwise unchanged.

## Packaging

`[free]` extra becomes `["edge-tts>=6", "faster-whisper>=1", "deep-translator>=1.11"]`.
Base install stays light. First-run guidance already points keyless users to `[free]`.

## Error handling

- Whisper: import/model-load failure → `ProviderUnavailable` (resolved earlier) or a clear
  runtime error surfaced via `log`; long audio handled natively by faster-whisper (no
  manual chunking needed).
- deep-translator: per-segment failure keeps the original text and logs; a total failure
  (e.g. no network) raises so the caller can surface it.
- Keyless + `[free]` absent → `transcribe_translate` raises the guidance error before any
  heavy work.

## Testing (mock all externals — no network, no model downloads)

- `WhisperProvider.transcribe`: monkeypatch a fake `faster_whisper.WhisperModel` yielding
  two segments; assert Subtitles built with correct ms timings and text; assert model
  cached (constructed once across two calls).
- `GoogleFreeProvider.translate`: monkeypatch `deep_translator.GoogleTranslator`; assert
  each `translated_text` filled; per-item error keeps original + logs.
- Gemini transcribe-only / translate-only: monkeypatch the genai client; assert schema
  parse builds Subtitles / fills translations.
- Resolution: `auto` with key → gemini; `auto` without key but free available → free;
  neither → raises. Explicit unavailable → raises.
- Combined fast-path: both gemini → `transcribe_and_translate` called once; mixed → asr
  then translate called.
- `public_config()` includes `asr_engines`/`translate_engines`, still no secrets.
- Backward-compat: existing `transcribe_and_translate` tests unchanged and green.

## Definition of done

- On a machine with **no API key** and `pip install translatedub[free]`, a full
  translate → dub runs end-to-end (whisper → deep-translator → edge/gtts).
- With a Gemini key, behavior is unchanged (single combined Gemini call).
- Mixed engine selections work (whisper + Gemini translate, Gemini ASR + deep-translator).
- All tests pass; ruff + bandit clean; CI matrix green.

## Spec self-review

- Placeholder scan: none.
- Consistency: provider attrs (`name`/`premium`/`is_available`) match Phase A; resolution
  policy matches the locked "Gemini-first" decision; `transcribe_translate` signature is
  used identically by both adapters.
- Scope: single phase, one subsystem (transcription). No unrelated refactors.
