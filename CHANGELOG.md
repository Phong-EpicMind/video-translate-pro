# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-07-02

### Added
- **Choose what to do before processing starts.** Uploading a video no longer
  auto-runs the pipeline: a new step shows the uploaded file and asks
  "Thuyết minh hay Chỉ phụ đề?", with the voice picker, voice preview, and
  burn-subtitles option right there. Processing starts only on "Bắt đầu xử lý".
- **Comfortable subtitle editing.** The translated column is now a growing
  multi-line textarea, and every row has an expand button that opens a large
  editor where both the original and the translated text can be edited.

### Changed
- On screens narrower than 1500px the editor stacks the video above the
  subtitle grid so the text columns stay wide enough to edit.

## [0.3.0] - 2026-07-02

### Added
- **Voice preview.** A "Nghe thử" button next to the voice picker synthesises a
  short sample with the exact engine + voice selected, so users can hear
  HoaiMy/NamMinh (or any voice) before dubbing. Samples are cached.

### Fixed
- **No more clipped words when lines are tight.** When a line is too long for
  its slot, the app now compresses speech exactly as much as needed (hard cap
  1.6x) instead of cutting the last words off; the boundary trim remains only
  as a last resort for extreme cases.

## [0.2.4] - 2026-07-02

### Changed
- Finished de-Googling the UI: the progress step "Gemini AI" is now "Nhận dạng
  & dịch", and the subtitle editor no longer says the translation comes from
  Gemini (it may come from any engine).

## [0.2.3] - 2026-07-02

### Fixed
- **The selected voice now reaches every engine.** The web UI only wired the
  voice choice to Google Cloud, so edge-tts silently ignored it (picking NamMinh
  still produced the default HoaiMy voice — or gTTS after a fallback).
- **Consecutive lines can no longer talk over each other.** Duration matching now
  aims at the gap until the next line starts (less speed-up, more natural), and
  the assembler trims any clip that would still spill into the next line with a
  short fade.

### Changed
- UI copy no longer brands the app as Google-only ("Integrated with Google AI
  APIs" etc.) — the engine lineup is pluggable by design.

## [0.2.2] - 2026-07-02

### Fixed
- **macOS folder picker now reliably opens in front.** `tell me to activate` was
  not enough for a dialog spawned by a background process (verified via System
  Events); the dialog is now hosted by Finder, which can truly activate. If
  Finder automation permission is denied, falls back to a plain dialog; a user
  cancel is respected and never reopens the dialog.

## [0.2.1] - 2026-07-02

### Fixed
- **Dubbed output could mix two voices.** edge-tts is rate-limited by Microsoft and
  fails transiently (`NoAudioReceived`); failed lines silently fell back to gTTS,
  producing a video that alternated between two voices. Synthesis now retries with
  backoff (rescues the vast majority of lines), and if a free engine still fails,
  the entire video is re-synthesised with one engine — output never mixes voices.
- **Folder picker could open twice.** The native dialog is now brought to the front
  (macOS), only one dialog can be open at a time (server-side lock + client-side
  button guard), and the dialog no longer blocks the web server's event loop.

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

[Unreleased]: https://github.com/Phong-EpicMind/video-translate-pro/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/Phong-EpicMind/video-translate-pro/releases/tag/v0.4.0
[0.3.0]: https://github.com/Phong-EpicMind/video-translate-pro/releases/tag/v0.3.0
[0.2.4]: https://github.com/Phong-EpicMind/video-translate-pro/releases/tag/v0.2.4
[0.2.3]: https://github.com/Phong-EpicMind/video-translate-pro/releases/tag/v0.2.3
[0.2.2]: https://github.com/Phong-EpicMind/video-translate-pro/releases/tag/v0.2.2
[0.2.1]: https://github.com/Phong-EpicMind/video-translate-pro/releases/tag/v0.2.1
[0.2.0]: https://github.com/Phong-EpicMind/video-translate-pro/releases/tag/v0.2.0
[0.1.2]: https://github.com/Phong-EpicMind/video-translate-pro/releases/tag/v0.1.2
[0.1.0]: https://github.com/Phong-EpicMind/video-translate-pro/releases/tag/v0.1.0
