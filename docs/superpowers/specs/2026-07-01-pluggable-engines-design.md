# Pluggable engine providers — design

**Date:** 2026-07-01
**Status:** Approved direction (verbal), spec for review before implementation
**Depends on:** the cross-platform CLI/web/library refactor (PR #10, merged into `main`)

## Goal

Let each pipeline stage — **transcribe (ASR)**, **translate**, **text-to-speech (TTS)** —
swap between engines behind a common interface, with a **zero-key default stack** so a
brand-new user can dub a video without configuring any API key. Premium engines stay
opt-in and unlock higher quality with the user's own key.

This mirrors the design of pyVideoTrans (~18k stars) and VideoLingo (~16k stars): a free
local/neural default, premium providers behind extras and keys.

| Stage | Free default (no key) | Premium (opt-in, user's own key) |
| --- | --- | --- |
| Transcribe | faster-whisper (local) | Gemini, OpenAI |
| Translate | deep-translator (Google free) | Gemini / LLM |
| TTS | **edge-tts** (free neural voices, incl. Vietnamese) | Google Cloud, OpenAI, ElevenLabs |

## Non-goals

- No change to the local-first / no-signing / env-var+`chmod 600` credential model.
- No VieNeu-TTS integration (DEFERRED — NeuTTS license open question, see CLAUDE.md).
- No vendoring or modifying edge-tts (LGPLv3): call its **CLI via subprocess**, attribute it.

## Phasing

The work ships in three self-contained increments, each independently testable and
mergeable. Only **Phase A** is fully specified here; B and C are outlined and will get
their own specs when we reach them.

- **Phase A — TTS provider seam + edge-tts default.** Introduce the provider pattern for
  the TTS stage only; make edge-tts the default free voice; keep gTTS as fallback and
  Google Cloud as premium. ASR/translate stay on Gemini exactly as today.
- **Phase B — free ASR + translate (`[local]` extra).** Add faster-whisper (ASR) and
  deep-translator (translate) providers so the whole pipeline runs with zero keys. This is
  where the combined Gemini "transcribe+translate" call is split into two stages.
- **Phase C — premium TTS providers.** OpenAI TTS and ElevenLabs providers (API key).

Rationale for starting with TTS: it is the smallest, lowest-risk seam (one function,
`synthesize_segment`), it delivers the most visible user win (natural Vietnamese neural
voice with no key), and it establishes the provider pattern that B and C reuse.

---

## Phase A — detailed design

### A.1 Provider abstraction (TTS)

New package `translatedub/core/providers/` with:

- `base.py` — the TTS provider contract:
  - `class TTSProvider(Protocol)` with:
    - `name: str` (registry key, e.g. `"edge"`)
    - `supports_native_rate: bool` — True when the engine can synthesize at an adjusted
      speaking rate (Google Cloud); False when rate is fixed and must be corrected
      post-hoc with ffmpeg `atempo` (gTTS, edge-tts).
    - `is_available(voice_config: dict) -> tuple[bool, str]` — returns `(available,
      reason)`. Reason is a human-readable hint when unavailable (e.g. `"edge-tts not
      installed — pip install translatedub[free]"`, or `"Google Cloud credentials
      missing"`).
    - `synthesize(text, lang, output_path, voice_config, speaking_rate) -> None` — raw
      synthesis of one segment; raises on failure. `speaking_rate` is honored only when
      `supports_native_rate` is True.
    - `default_voice(lang: str) -> str | None` — per-language default voice id.
  - A small `ProviderUnavailable(Exception)` for clean fallback control flow.

- `tts.py` — the registry and the concrete providers:
  - `GTTSProvider` — wraps the existing `gTTS` call. `supports_native_rate = False`.
  - `EdgeTTSProvider` — calls the `edge-tts` **CLI via subprocess**
    (`edge-tts --voice <v> --text <t> --write-media <out>`), never imports the package.
    `supports_native_rate = False`. `is_available` checks the CLI resolves on PATH
    (cache the result). Vietnamese default voice: `vi-VN-HoaiMyNeural` (female) with
    `vi-VN-NamMinhNeural` available as an alternative; English default
    `en-US-AriaNeural`; keep a small `_EDGE_LANG_DEFAULTS` map mirroring `_CLOUD_LANG`.
  - `GoogleCloudProvider` — wraps the existing Google Cloud path.
    `supports_native_rate = True`.
  - `REGISTRY: dict[str, TTSProvider]` and `get_tts_provider(name) -> TTSProvider`.
  - `available_tts_engines(config) -> list[dict]` — `[{name, available, reason,
    premium}]`, used by config/UI to show which engines are usable right now.

### A.2 `synthesize_segment` becomes a thin orchestrator

`core/tts.py` keeps `synthesize_segment(...)` as the **duration-matching orchestrator**
(the clamp/tolerance/atempo logic stays here, unchanged in behavior) but delegates raw
synthesis to the resolved provider:

1. Resolve provider via `get_tts_provider(engine)`. If the requested engine is
   unavailable, fall back per A.4 (never hard-fail on a missing free engine).
2. Call `provider.synthesize(...)` at `base_speed` (or adjusted rate if the provider
   supports native rate).
3. Measure duration. If `match_duration` and over the tolerance window:
   - `supports_native_rate` → re-synthesize at the clamped adjusted rate.
   - else → `change_tempo` (ffmpeg `atempo`) exactly as today.

This preserves the current MIN_SPEED/MAX_SPEED/SPEED_TOLERANCE constants and the existing
gTTS/Cloud behavior bit-for-bit; edge-tts simply reuses the fixed-rate (atempo) path.

### A.3 edge-tts as the default engine

- `config.DEFAULT_SETTINGS["tts_engine"]` changes `"gtts"` → `"edge"`.
- edge-tts is an **optional dependency** (LGPLv3), installed via a new extra:
  `pip install translatedub[free]` (also the umbrella extra Phase B will extend with
  faster-whisper + deep-translator). Base install stays light and does **not** pull
  edge-tts.
- Because the default engine may not be installed on a base install, the resolver
  (A.4) transparently falls back to gTTS with a one-line guidance message. So: default is
  edge **the moment it is available**; base users still get working audio via gTTS and a
  nudge to install `[free]` for the better neural voice.

### A.4 Engine resolution & fallback order

Given a requested engine name and the current config:

1. If requested engine is available → use it.
2. Else if requested is a **free** engine (`edge`/`gtts`) → fall back to the other free
   engine that is available, logging: `"<engine> unavailable (<reason>); using <fallback>.
   For neural voices: pip install translatedub[free]"`.
3. Else (a **premium** engine requested but unavailable, e.g. missing Cloud creds) →
   raise a clear error (do not silently downgrade a paid choice the user explicitly set).

Free engines degrade gracefully; premium engines fail loudly. This keeps the zero-key
promise while never surprising a user who deliberately picked a premium voice.

### A.5 Surfaced state (config / UI / CLI)

- `public_config()` gains `tts_engines: available_tts_engines(config)` (names + availability
  + premium flag + reason). No secret values — consistent with the existing contract.
- Web UI: the engine/voice control lists engines from `tts_engines`, disables unavailable
  ones with the reason as a tooltip, defaults to edge when available. The SSE/JSON event
  contract is unchanged; only the config payload gains the additive `tts_engines` field so
  `static/js/main.js` keeps working (update both sides together).
- CLI: `--engine` accepts `edge` (in addition to `gtts`, `google_cloud`); `--voice`
  passes an edge voice id through `voice_config`. `translatedub config show` lists engine
  availability.

### A.6 Packaging & attribution

- `pyproject.toml`: add extra `free = ["edge-tts>=6"]`. Keep `cloud` and `dev` as-is.
- `THIRD_PARTY_NOTICES.md`: record edge-tts (LGPLv3), noting it is optional, unmodified,
  and invoked via its CLI. (CLAUDE.md already states the licensing conclusion.)
- First-run guidance: when no premium key and edge-tts is absent, print the
  "free & private → pip install translatedub[free]" vs "cloud → add a key" hint.

### A.7 Error handling

- All raw synthesis raises on failure; `synthesize_segment` catches and reports via `log`,
  returning `False` exactly as today (pipeline turns that into a per-line `RuntimeError`).
- edge-tts subprocess: capture stderr, surface a trimmed message; treat non-zero exit or
  missing output file as failure → triggers free-engine fallback on the *first* line only
  (cache availability so we do not retry the CLI for every segment).
- Network failures from edge-tts (it calls Microsoft's online endpoint) are reported like
  any other synthesis error; the user can switch to gTTS or a premium engine.

### A.8 Testing (no network, no ffmpeg, mock all externals)

- Registry: `get_tts_provider` resolves known names; unknown → clear error.
- Availability: `is_available` correctly reports missing edge CLI / missing Cloud creds
  (monkeypatch PATH lookup and config).
- Fallback: requested `edge` unavailable → resolves to `gtts` with the guidance log;
  requested `google_cloud` unavailable → raises.
- edge provider: subprocess is mocked; assert the argv (voice, text, `--write-media`
  path) and that a missing output file is treated as failure.
- Orchestrator: duration-matching path selection — native-rate provider re-synthesizes;
  fixed-rate provider calls `change_tempo` (both mocked).
- `public_config()` includes `tts_engines` and still exposes **no** secret values.

### A.9 Definition of done (Phase A)

- Default dub on a fresh machine with `pip install translatedub[free]` and a Gemini key
  produces a natural Vietnamese neural voice with **no** Google Cloud setup.
- Base install (no `[free]`) still works via gTTS with a visible nudge.
- Google Cloud premium path unchanged.
- All existing tests pass; new tests above pass; ruff + bandit clean; CI matrix green.

---

## Phase B — outline (free ASR + translate, added to the `[free]` extra)

- Split the combined Gemini `transcribe_and_translate` into two provider stages:
  - **ASR**: `WhisperProvider` (faster-whisper, `[local]`) returns original text +
    timings; `GeminiASRProvider` keeps the current behavior.
  - **Translate**: `GoogleFreeProvider` (deep-translator) and `GeminiTranslateProvider`.
  - A **combined** capability lets Gemini keep doing ASR+translate in one call when both
    stages are set to Gemini (no double cost/latency regression).
- `[free]` extra gains `faster-whisper` (MIT) + `deep-translator` (Apache-2.0). Model
  weights (Whisper, MIT) download on first use.
- Full zero-key stack after this phase: faster-whisper + deep-translator + edge-tts.

## Phase C — outline (premium TTS)

- `OpenAITTSProvider` and `ElevenLabsProvider` (API key via the existing secret model;
  new secret keys added to `SECRET_KEYS` and `_ENV_OVERRIDES`). Both `supports_native_rate`
  handling per their APIs. No license risk (user brings key, accepts provider ToS).

## Resolved decisions (2026-07-01)

- **Default Vietnamese voice:** `vi-VN-HoaiMyNeural` (female). Expose
  `vi-VN-NamMinhNeural` (male) as the alternate in the UI voice list.
- **Packaging:** a **single `[free]` umbrella extra** for all zero-key engines — edge-tts
  in Phase A, faster-whisper + deep-translator added to the same extra in Phase B. One
  onboarding command: `pip install translatedub[free]`. (No separate `[local]` extra.)
