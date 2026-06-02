# TranslateDub AI

<p align="center">
  <strong>Native macOS video translation, subtitle editing, and AI dubbing for creators.</strong>
</p>

<p align="center">
  Translate videos into another language, review subtitles, generate a dubbed voice track, and export a ready-to-share video from a local macOS desktop app.
</p>

<p align="center">
  <a href="https://github.com/Phong-EpicMind/video-translate-pro/releases/latest"><strong>Download latest macOS DMG</strong></a>
  ·
  <a href="#quick-start">Quick Start</a>
  ·
  <a href="#tieng-viet">Tiếng Việt</a>
  ·
  <a href="SECURITY.md">Security</a>
  ·
  <a href="THIRD_PARTY_NOTICES.md">Third-party Notices</a>
</p>

<p align="center">
  <a href="https://github.com/Phong-EpicMind/video-translate-pro/releases/latest">
    <img alt="Latest release" src="https://img.shields.io/github/v/release/Phong-EpicMind/video-translate-pro?label=latest%20release">
  </a>
  <a href="https://github.com/Phong-EpicMind/video-translate-pro/actions/workflows/ci.yml">
    <img alt="CI" src="https://github.com/Phong-EpicMind/video-translate-pro/actions/workflows/ci.yml/badge.svg">
  </a>
  <a href="https://github.com/Phong-EpicMind/video-translate-pro/actions/workflows/security.yml">
    <img alt="Security scan" src="https://github.com/Phong-EpicMind/video-translate-pro/actions/workflows/security.yml/badge.svg">
  </a>
  <a href="LICENSE">
    <img alt="Source license: MIT" src="https://img.shields.io/badge/source%20license-MIT-green">
  </a>
  <img alt="Platform" src="https://img.shields.io/badge/platform-macOS%20arm64-black">
</p>

---

## Download

The current public build is **TranslateDub AI v0.1.2** for **macOS Apple Silicon arm64**.

| What you need | Link |
| --- | --- |
| Installable app | [TranslateDub_AI_macOS_arm64_v0.1.2.dmg](https://github.com/Phong-EpicMind/video-translate-pro/releases/download/v0.1.2/TranslateDub_AI_macOS_arm64_v0.1.2.dmg) |
| Release page | [TranslateDub AI v0.1.2](https://github.com/Phong-EpicMind/video-translate-pro/releases/tag/v0.1.2) |
| Checksums | [SHA256SUMS.txt](https://github.com/Phong-EpicMind/video-translate-pro/releases/download/v0.1.2/SHA256SUMS.txt) |

> macOS notice: this build is ad-hoc signed but not Apple Developer ID signed or notarized yet. On first launch, macOS may require **Control-click > Open**.

## What It Does

TranslateDub AI is a local-first macOS desktop application for video translation and dubbing workflows:

1. Import a local video file.
2. Extract audio with bundled FFmpeg.
3. Transcribe and translate speech with Google Gemini.
4. Review and edit bilingual subtitles.
5. Generate a dubbed voice track with gTTS or Google Cloud Text-to-Speech.
6. Export a translated video with optional burned-in subtitles.

It is an independent implementation inspired by the general workflow of [pyVideoTrans](https://github.com/jianchang512/pyvideotrans). It does not vendor or depend on pyVideoTrans source code, assets, or binaries.

## Highlights

| Area | Details |
| --- | --- |
| Desktop experience | Native macOS window powered by PyWebView and a FastAPI local backend |
| Translation workflow | Gemini-based speech transcription and translation with chunking for longer videos |
| Subtitle review | Interactive subtitle editor with original and translated text side by side |
| Dubbing | gTTS fallback plus Google Cloud Text-to-Speech voice support |
| Video processing | Bundled FFmpeg and FFprobe in packaged macOS releases |
| Privacy | Credentials are stored in macOS Keychain, not in the repository or release bundle |
| Release hygiene | CI, Bandit scan, checksums, third-party notices, and FFmpeg corresponding source archive |

## Quick Start

1. Download the latest `.dmg` from [GitHub Releases](https://github.com/Phong-EpicMind/video-translate-pro/releases/latest).
2. Open the `.dmg`.
3. Drag **TranslateDub AI** into **Applications**.
4. Open the app.
5. Add your Gemini API key. If using premium Google Cloud TTS, add a Google Cloud Service Account JSON with Text-to-Speech access.
6. Drop in a video and run the translation workflow.

## Requirements

| Requirement | Notes |
| --- | --- |
| macOS | Current packaged build targets Apple Silicon arm64 |
| Gemini API key | Required for transcription and translation |
| Google Cloud Text-to-Speech credentials | Optional, only needed for Google Cloud TTS voices |
| FFmpeg | Bundled in the `.dmg`; Homebrew FFmpeg is only needed for local development |

## Security And Privacy

TranslateDub AI is designed as a local desktop app. The app does not ship with API keys or service account files.

| Data | Handling |
| --- | --- |
| Gemini API key | Stored in macOS Keychain under `com.phongho.translatedubai` |
| Google Cloud Service Account JSON | Stored in macOS Keychain under `com.phongho.translatedubai` |
| Non-secret preferences | Stored in `~/.translatedub_ai/config.json` with owner-only file permissions |
| Temporary media | Stored under `~/.translatedub_ai/temp` |
| GitHub releases | Checked for accidental `config.json` or credential JSON files before publishing |

See [SECURITY.md](SECURITY.md) for the vulnerability reporting process.

## Build From Source

```bash
git clone https://github.com/Phong-EpicMind/video-translate-pro.git
cd video-translate-pro
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python desktop.py
```

For local development, install FFmpeg:

```bash
brew install ffmpeg
```

To create a local macOS app bundle:

```bash
./venv/bin/pyinstaller -y --noconsole --name "TranslateDub AI" \
  --icon "static/icon.icns" \
  --add-data "templates:templates" \
  --add-data "static:static" \
  --add-data "LICENSE:." \
  --add-data "THIRD_PARTY_NOTICES.md:." \
  --add-data "FFMPEG_SOURCE_OFFER.md:." \
  --add-binary "bin/ffmpeg:bin" \
  --add-binary "bin/ffprobe:bin" \
  desktop.py
```

## Licensing

The TranslateDub AI source code is distributed under the [MIT License](LICENSE).

Packaged macOS releases may include third-party binaries and libraries under their own licenses. In particular, the release `.dmg` bundles FFmpeg and FFprobe binaries that report `--enable-gpl --enable-version3`; these are treated as GPL-3.0 components. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [FFMPEG_SOURCE_OFFER.md](FFMPEG_SOURCE_OFFER.md).

## Project Links

| Resource | Link |
| --- | --- |
| Releases | [GitHub Releases](https://github.com/Phong-EpicMind/video-translate-pro/releases) |
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Security | [SECURITY.md](SECURITY.md) |
| Code of Conduct | [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) |
| Release checklist | [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) |
| Third-party notices | [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) |

---

<a id="tieng-viet"></a>

## Tiếng Việt

**TranslateDub AI** là ứng dụng desktop macOS giúp dịch video, biên tập phụ đề song ngữ, tạo giọng lồng tiếng bằng AI và xuất video đã dịch từ một quy trình cục bộ trên máy Mac.

### Tải về

Bản public hiện tại là **TranslateDub AI v0.1.2** cho **macOS Apple Silicon arm64**.

| Nội dung | Link |
| --- | --- |
| File cài đặt | [TranslateDub_AI_macOS_arm64_v0.1.2.dmg](https://github.com/Phong-EpicMind/video-translate-pro/releases/download/v0.1.2/TranslateDub_AI_macOS_arm64_v0.1.2.dmg) |
| Trang release | [TranslateDub AI v0.1.2](https://github.com/Phong-EpicMind/video-translate-pro/releases/tag/v0.1.2) |
| Kiểm tra checksum | [SHA256SUMS.txt](https://github.com/Phong-EpicMind/video-translate-pro/releases/download/v0.1.2/SHA256SUMS.txt) |

> Lưu ý macOS: bản hiện tại đã ký ad-hoc nhưng chưa Apple Developer ID signed/notarized. Lần đầu mở app có thể cần **Control-click > Open**.

### Ứng dụng làm được gì

1. Chọn hoặc kéo thả video trên máy Mac.
2. Tách âm thanh bằng FFmpeg được bundle sẵn trong bản `.dmg`.
3. Nhận dạng lời nói và dịch bằng Google Gemini.
4. Biên tập phụ đề gốc và bản dịch trong giao diện song ngữ.
5. Tạo track lồng tiếng bằng gTTS hoặc Google Cloud Text-to-Speech.
6. Xuất video đã lồng tiếng, có tùy chọn gắn phụ đề vào video.

Đây là một dự án độc lập, lấy cảm hứng từ quy trình tổng quát của [pyVideoTrans](https://github.com/jianchang512/pyvideotrans). Repo này không vendor, copy, hay phụ thuộc vào source code, asset, hoặc binary của pyVideoTrans.

### Hướng dẫn cài đặt nhanh

1. Tải file `.dmg` mới nhất tại [GitHub Releases](https://github.com/Phong-EpicMind/video-translate-pro/releases/latest).
2. Mở file `.dmg`.
3. Kéo **TranslateDub AI** vào thư mục **Applications**.
4. Mở app.
5. Nhập Gemini API key. Nếu dùng Google Cloud TTS, nhập thêm Google Cloud Service Account JSON có quyền Text-to-Speech.
6. Đưa video vào app và chạy quy trình dịch.

### Bảo mật

| Dữ liệu | Cách xử lý |
| --- | --- |
| Gemini API key | Lưu trong macOS Keychain với service `com.phongho.translatedubai` |
| Google Cloud Service Account JSON | Lưu trong macOS Keychain với service `com.phongho.translatedubai` |
| Cấu hình không nhạy cảm | Lưu tại `~/.translatedub_ai/config.json` với quyền chỉ chủ máy đọc/ghi |
| File tạm | Lưu trong `~/.translatedub_ai/temp` |
| Release GitHub | Kiểm tra không bundle nhầm `config.json` hoặc file credential JSON |

### Giấy phép

Source code của TranslateDub AI được phát hành theo [MIT License](LICENSE). Bản `.dmg` có thể kèm các thành phần bên thứ ba theo license riêng, đặc biệt là FFmpeg/FFprobe theo GPL-3.0. Xem [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) và [FFMPEG_SOURCE_OFFER.md](FFMPEG_SOURCE_OFFER.md).
