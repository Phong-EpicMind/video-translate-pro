# TranslateDub AI — Cross-platform CLI + Web refactor

Date: 2026-07-01
Status: Approved (design), in implementation
Branch: `refactor/cross-platform-cli`

## Goal

Turn the current macOS-only downloadable desktop app (PyWebView + PyInstaller `.dmg`)
into an **open-source, cross-platform, pip-installable tool** that runs on macOS,
Windows, and Linux with **no code signing, no paid certificate, and no repeated
Keychain prompts**, while keeping the existing translation/dubbing engine and web UI.

Secondary goal: shape the project so it reads as a *developer-friendly, embeddable
tool* (better fit for GitHub stars and the Anthropic/OpenAI open-source maintainer
programs), while a one-command web UI keeps it usable by non-technical video creators.

## Non-goals

- No Apple Developer ID signing / notarization (paid, explicitly out of scope forever).
- No hosted SaaS: stays **local-first** — user media and API keys never leave the machine.
- No rewrite of the translation/dubbing logic; this is a restructure, not a redesign.

## Why (root cause being fixed)

The repeated macOS Keychain prompt ("wants to use your confidential information")
is caused by ad-hoc code signing: an ad-hoc binary's code hash changes every build,
and Keychain ACLs are bound to the signing identity's Designated Requirement, so
"Always Allow" never sticks. The only real fixes are (a) a stable Developer ID
(paid) or (b) stop depending on the Keychain ACL. We choose (b): store credentials
the way standard CLI tools (`gh`, `aws`, `npm`) do — env var + `chmod 600` file.

## Target UX

```
pip install translatedub          # or: pipx install translatedub / uvx translatedub
translatedub config set-key        # store Gemini key (prompted, hidden input)
translatedub translate video.mp4 --to vi -o out.mp4   # one-shot CLI
translatedub serve                 # opens the web UI in the default browser
```

Python library use:

```python
from translatedub.core import transcribe_and_translate, synthesize, mux
```

## Architecture

Local-first. Three consumers over one engine core.

```
translatedub/
  __init__.py            # version, public exports
  __main__.py            # python -m translatedub -> cli.main()
  cli.py                 # argparse commands: translate | dub | serve | config
  config.py              # env var + chmod-600 JSON file; no keychain
  ffmpeg.py              # cross-platform ffmpeg/ffprobe resolution (system or imageio-ffmpeg)
  core/
    __init__.py          # public engine API
    subtitles.py         # SRT time helpers, SRT writer, Subtitle dataclass
    media.py             # extract audio, duration, has-audio, mux, burn/soft subs
    transcribe.py        # Gemini transcription + translation (with chunking + retry)
    tts.py               # gTTS + Google Cloud TTS, duration matching
  web/
    __init__.py
    server.py            # FastAPI app (localhost-only), SSE endpoints, opens browser
    templates/index.html # moved from repo-root templates/
    static/...           # moved from repo-root static/
tests/                   # pytest suite
pyproject.toml           # packaging, entry point, deps
```

### Module boundaries

- `core/` knows nothing about web or CLI. Pure functions + small dataclasses. Fully testable.
- `config.py` is the only place that reads/writes credentials. No secret ever printed or logged.
- `ffmpeg.py` is the only place that resolves binary paths.
- `web/server.py` and `cli.py` are thin adapters over `core/`.

## Credential storage (final decision)

Resolution order when a secret is needed:

1. Environment variable (`TRANSLATEDUB_GEMINI_KEY`, then legacy `GEMINI_API_KEY`).
2. `~/.translatedub/config.json`, created with `0o600`, directory `0o700`.

- Plaintext in the file — this is the industry norm for local CLI tools. On-disk
  "encryption" without a user passphrase is obfuscation, not security, so we do not
  fake it. Real optional passphrase-based encryption may be added later (out of scope now).
- Windows: same JSON file under `%USERPROFILE%\.translatedub\`. `chmod` is a no-op on
  Windows; we rely on the per-user profile directory ACL (standard for `gh`, `aws`).
- `config.py` never returns secrets in any "public config" surfaced to the web UI;
  the UI only sees booleans `has_gemini_key` / `has_google_cloud_credentials`.
- The macOS `Security`/Keychain code path is removed entirely.

## FFmpeg (cross-platform, no bundled 127 MB binaries)

`ffmpeg.py` resolves binaries in this order:

1. System `ffmpeg`/`ffprobe` on `PATH` (or common install dirs).
2. Fallback: [`imageio-ffmpeg`](https://pypi.org/project/imageio-ffmpeg/) provides a
   per-platform static `ffmpeg` binary (a widely used, pip-installable dependency).

`ffprobe` is not guaranteed by `imageio-ffmpeg`. To avoid a hard `ffprobe` dependency,
`media.py` derives duration and audio-stream presence from `ffmpeg -i` stderr parsing
when `ffprobe` is absent, and uses `ffprobe` when it is available. The bundled `bin/`
binaries are dropped from the package (kept out of the wheel).

## Distribution

- Publish to **PyPI**; document `pip` / `pipx` / `uvx` install.
- No Gatekeeper/SmartScreen friction (source/wheel install, not a downloaded app bundle).
- Optional Homebrew formula later (a Python CLI formula needs no signing).

## Testing (industry standard)

- `pytest` unit tests for pure logic: SRT time round-trip, SRT writer output,
  filename sanitisation, unique-output-path, config read/write + permission bits,
  secret resolution order (env over file), ffmpeg path resolution (mocked),
  subtitle chunk offset/re-indexing, TTS duration-matching speed math (mocked ffmpeg).
- External calls (Gemini, Google Cloud, ffmpeg subprocess) are mocked; no network in tests.
- GitHub Actions CI: run tests on Ubuntu + macOS + Windows across supported Python
  versions; keep the existing Bandit security scan.
- Target: all pure logic covered; adapters smoke-tested by importing and invoking with mocks.

## Cleanup / safety (this change)

- Removed repo-root `config.json` that held live Gemini + GCP keys (rotate advised).
- Remove stale `dist/`, `build/`, `*.app`, `*.spec`, `bin/`, PyWebView + PyInstaller deps.
- Remove macOS-only code: hardcoded `/opt/homebrew` PATH juggling, `open -R` reveal,
  `Security` framework Keychain integration.
- Update `.gitignore`, `README.md` (dev-first, cross-platform), `requirements` → `pyproject.toml`.

## Risks / mitigations

- **ffmpeg stderr parsing fragility** → prefer `ffprobe` when present; parser is only a fallback and is unit-tested against captured sample output.
- **Scope is large** → implement in phases (core → config → ffmpeg → cli → web → packaging → tests → docs), each independently testable, committed incrementally.
- **Behavioral regressions vs current app** → keep the same SSE/JSON contract the existing `static/js/main.js` expects so the web UI keeps working unchanged.
