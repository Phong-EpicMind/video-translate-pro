# CLAUDE.md — Working notes for AI agents & contributors

Guidance for anyone (human or AI) working on **TranslateDub AI**. Keep it current.

## What this is

Local-first, **cross-platform** (macOS / Windows / Linux) video translation, subtitling,
and AI dubbing. Ships as a Python package `translatedub` installable via `pip`/`pipx`/`uvx`.
Three ways to use it: **CLI** (`translatedub translate ...`), **local web UI**
(`translatedub serve`, opens the default browser), and **library** (`from translatedub.core import ...`).

Repo: `Phong-EpicMind/video-translate-pro`. Independent implementation inspired by the
general workflow of pyVideoTrans — no pyVideoTrans code/assets/binaries are used.

## Non-negotiable principles

- **Open source forever, MIT.** No paid dependencies required to use the app.
- **No code signing / notarization** (paid, rejected on purpose). Distribution is via
  PyPI, so there is no Gatekeeper/SmartScreen friction anyway.
- **Local-first.** User video and API keys never leave the machine. No project-run server
  ever receives user media or keys. The web server binds to `127.0.0.1` only.
- **Cross-platform.** No macOS-only code. No hardcoded `/opt/homebrew` paths, no
  `open -R`, no `Security`/Keychain. Guard OS-specific bits (`sys.platform` / `os.name`).
- **Low barrier to entry.** A new user should be able to run the tool with **zero API keys**
  (see engine roadmap). Keys unlock higher quality, they are never required to start.

## Architecture

```
translatedub/
  cli.py            argparse: translate | serve | config
  config.py         credential + settings storage (see below)
  ffmpeg.py         resolve system ffmpeg/ffprobe, else imageio-ffmpeg fallback
  filenames.py      filesystem-safe name helpers
  pipeline.py       high-level orchestration shared by CLI + web
  core/             web/CLI-agnostic engine (pure, fully unit-tested)
    subtitles.py    Subtitle dataclass + SRT helpers
    media.py        ffmpeg ops: extract audio, probe, mux, subtitles
    transcribe.py   Gemini transcription + translation (chunked, retried)
    tts.py          gTTS + Google Cloud TTS (+ duration matching)
    assemble.py     overlay per-segment TTS clips into one dubbed track
  web/
    server.py       FastAPI app; same SSE/JSON contract the frontend expects
    templates/, static/   the single-page UI (moved from repo root)
```

`core/` never imports web or CLI. `cli.py` and `web/server.py` are thin adapters over
`core/` + `pipeline.py`. Keep it that way.

## Credential model (do NOT reintroduce Keychain)

Secrets resolve **env var first, then `~/.translatedub/config.json`** (created `0o600`,
dir `0o700`). This mirrors `gh`/`aws`/`npm`. Rationale: the old macOS Keychain path
re-prompted on every launch under ad-hoc signing and added no real security for a local
app. On-disk secrets are plaintext by design (encrypting without a user passphrase is
obfuscation). Env vars: `TRANSLATEDUB_GEMINI_KEY`/`GEMINI_API_KEY`,
`TRANSLATEDUB_GOOGLE_CLOUD_CREDENTIALS`/`GOOGLE_APPLICATION_CREDENTIALS`.
`config.public_config()` must never expose secret values — only `has_*` booleans.

## Engine roadmap (planned pluggable providers)

Goal: a provider abstraction so each pipeline stage (ASR / translate / TTS) can swap
engines, with a **zero-key default stack** and optional premium providers. Model after
pyVideoTrans (~18k stars) and VideoLingo (~16k stars).

| Stage | Free default (no key) | Premium (opt-in, user's own key) |
| --- | --- | --- |
| Transcribe | faster-whisper (local) | Gemini, OpenAI |
| Translate | deep-translator (Google free) | Gemini/LLM |
| TTS | **edge-tts** (free neural voices, incl. Vietnamese) | Google Cloud, OpenAI TTS, ElevenLabs |

- edge-tts should become the default free voice (replaces gTTS as default; gTTS may stay
  as a fallback).
- Package extras: heavy/optional engines behind extras (`[local]` for faster-whisper,
  `[cloud]` for Google Cloud, etc.) so the base install stays light. First-run with no
  engine configured should guide the user: "free & private → `pip install ...[local]`"
  vs "cloud → add a key".

## Licensing rules (CRITICAL — the maintainer is strict about this)

Verify licenses **from source** (the actual LICENSE file / HF model-card metadata),
never assume from a repo's headline claim. Only add dependencies with permissive licenses
(MIT / BSD / Apache-2.0). Record every third-party component in `THIRD_PARTY_NOTICES.md`.

Verified as of 2026-07-01:
- faster-whisper **MIT**, deep-translator **Apache-2.0**, Whisper weights **MIT**,
  imageio-ffmpeg **BSD** — clean.
- **edge-tts is LGPLv3** (not GPL). Usable, but keep it an **optional** dependency,
  **do not vendor or modify** it, prefer calling its CLI via subprocess, and attribute it.
  Do not copy edge-tts source into this repo.
- FFmpeg is **not bundled** by this project (system or `imageio-ffmpeg`), so no GPL
  corresponding-source obligation attaches to our distribution.
- **VieNeu-TTS (Vietnamese on-device TTS): DEFERRED.** Its weights chain is Apache-2.0
  (Qwen 0.5B → NeuTTS Air weights → VieNeu), BUT Neuphonic's NeuTTS *toolkit code* uses a
  custom "NeuTTS Open License v1.0" that restricts large-revenue commercial use. Before
  integrating, confirm VieNeu's pip package does not pull that restricted toolkit code, or
  ask the author (Phạm Nguyễn Ngọc Bảo). Prefer VieNeu v3 (from-scratch, non-NeuTTS) once
  stable. Do not integrate VieNeu until this is resolved in writing.
- **API providers (OpenAI, ElevenLabs, Google Cloud, etc.) have no license risk** — the
  user brings their own key and accepts the provider's ToS. We only ship an API client.

## Dev commands

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev,cloud]"
pytest                          # unit tests; external calls are mocked, no network
ruff check translatedub tests
bandit -r translatedub -ll
translatedub serve --no-browser # manual smoke test
```

## Testing standards

- Pure logic in `core/` and `config.py` must be unit-tested. Mock all external calls
  (Gemini, cloud TTS, ffmpeg subprocess); tests must not hit the network or need ffmpeg.
- CI matrix: Ubuntu/macOS/Windows × Python 3.9/3.11/3.12, plus Bandit and a hygiene job
  that blocks tracked secrets/build artifacts. Keep it green before merging.
- Bump the version in both `pyproject.toml` and `translatedub/__init__.py` on release.

## Conventions

- Match the surrounding code style; keep modules small and single-purpose.
- Never commit secrets, generated media, `config.json`, or build artifacts (see `.gitignore`).
- Keep the web SSE/JSON event contract stable so `static/js/main.js` keeps working, or
  update both sides together.
- Design specs live in `docs/superpowers/specs/`.
