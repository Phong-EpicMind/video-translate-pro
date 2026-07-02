# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-07-02

First release as a cross-platform pip package (`translatedub`).

### Added
- **Zero-key pipeline** via the `[free]` extra: local speech recognition
  (faster-whisper), free translation (deep-translator), and free neural voices
  including Vietnamese (edge-tts, default voice `vi-VN-HoaiMyNeural`). No API key
  required to transcribe, translate, and dub.
- Pluggable provider architecture for ASR / translation / TTS
  (`translatedub.core.providers`): engines are selectable per stage, `auto`
  prefers Gemini when a key is present and the free local stack otherwise.
- Three interfaces: CLI (`translatedub translate ...`), local web UI
  (`translatedub serve`, bound to `127.0.0.1` only), and Python library
  (`translatedub.core` / `translatedub.pipeline`).
- Native folder picker and reveal-in-file-manager in the web UI on
  macOS / Windows / Linux.
- Engine selection flags in the CLI (`--asr-engine`, `--translate-engine`,
  `--whisper-model`, `--engine`) and matching selectors in the web UI.
- Optional premium engines: Gemini (transcribe + translate) and Google Cloud TTS
  (`[cloud]` extra).

### Changed
- Distribution is now a Python package (pip / pipx / uvx) instead of a
  platform-specific desktop bundle; runs on macOS, Windows, and Linux.
- Credentials resolve from environment variables first, then
  `~/.translatedub/config.json` (created `chmod 600`) — same model as `gh`/`aws`.
- Free TTS engines degrade gracefully (edge-tts falls back to gTTS on failure);
  premium engines fail loudly.

### Removed
- macOS-only desktop app packaging (PyWebView / PyInstaller `.dmg`) and the
  Keychain credential store.

## [0.1.2] - 2026-06-02

- Last release of the macOS desktop app line (`.dmg`). Superseded by the
  cross-platform pip package above.

## [0.1.0] - 2026-06-01

- Initial public prototype: macOS desktop app for video translation, subtitle
  editing, and AI dubbing with Gemini + gTTS / Google Cloud TTS.

[Unreleased]: https://github.com/Phong-EpicMind/video-translate-pro/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Phong-EpicMind/video-translate-pro/releases/tag/v0.2.0
[0.1.2]: https://github.com/Phong-EpicMind/video-translate-pro/releases/tag/v0.1.2
[0.1.0]: https://github.com/Phong-EpicMind/video-translate-pro/releases/tag/v0.1.0
