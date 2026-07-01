# TranslateDub AI

**Local-first, cross-platform video translation, subtitling, and AI dubbing — as a CLI, a Python library, or a one-command local web app.**

Translate a video into another language, review the bilingual subtitles, generate a
dubbed voice track, and export a ready-to-share video — all on your own machine.
Your video files and API keys never leave your computer.

<p align="center">
  <a href="https://github.com/Phong-EpicMind/video-translate-pro/actions/workflows/ci.yml">
    <img alt="CI" src="https://github.com/Phong-EpicMind/video-translate-pro/actions/workflows/ci.yml/badge.svg">
  </a>
  <a href="https://github.com/Phong-EpicMind/video-translate-pro/actions/workflows/security.yml">
    <img alt="Security scan" src="https://github.com/Phong-EpicMind/video-translate-pro/actions/workflows/security.yml/badge.svg">
  </a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-green"></a>
  <img alt="Python" src="https://img.shields.io/badge/python-3.9%2B-blue">
  <img alt="Platforms" src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-black">
</p>

---

## Install

Requires **Python 3.9+**. No code signing, no downloads to unblock, no admin rights.

```bash
pipx install translatedub          # recommended (isolated), or:
pip install translatedub
# run once without installing:
uvx translatedub serve
```

FFmpeg is resolved automatically: it uses a system `ffmpeg` if present, otherwise the
bundled-per-platform binary from the `imageio-ffmpeg` dependency. Nothing extra to install.

For premium Google Cloud voices, install the optional extra:

```bash
pip install "translatedub[cloud]"
```

## Quick start

```bash
# 1. Store your Gemini API key (kept in a chmod 600 file, never in the repo)
translatedub config set-key

# 2a. Translate + dub a video in one command
translatedub translate input.mp4 --to vi -o output.mp4

# 2b. …or open the visual editor in your browser (edit subtitles before export)
translatedub serve
```

Get a free Gemini key at [Google AI Studio](https://aistudio.google.com/).

## Three ways to use it

| Mode | Command | Best for |
| --- | --- | --- |
| **CLI** | `translatedub translate ...` | scripting, batch, power users |
| **Web UI** | `translatedub serve` | reviewing/editing subtitles, non-technical users |
| **Library** | `from translatedub.core import ...` | embedding in your own tools |

### CLI examples

```bash
# Subtitles only (no dubbing), burned into the video
translatedub translate talk.mp4 --to en --subtitles-only --burn-subtitles

# Premium Google Cloud voice, keep 20% of the original audio under the dub
translatedub translate vlog.mp4 --to vi --engine google_cloud \
  --voice vi-VN-Neural2-A --original-vol 0.2

# See all options
translatedub translate --help
```

### Library example

```python
from translatedub.pipeline import translate_video, export_video

subs = translate_video("input.mp4", "auto", "vi", gemini_key="...")
for s in subs:
    print(s.index, s.translated_text)          # review / edit programmatically
export_video("input.mp4", subs, "output.mp4", target_lang="vi")
```

## How it works

1. Extract audio with FFmpeg.
2. Transcribe and translate speech with **Google Gemini** (auto-chunked for long videos).
3. Review/edit bilingual subtitles (in the web UI) or use them directly (CLI/library).
4. Generate a dubbed voice track with **gTTS** (free) or **Google Cloud TTS** (premium),
   with optional duration matching so speech fits each subtitle window.
5. Mux the dub over the original video, with optional burned-in or soft subtitles.

This is an independent implementation inspired by the general workflow of
[pyVideoTrans](https://github.com/jianchang512/pyvideotrans). It does not vendor or
depend on pyVideoTrans source code, assets, or binaries.

## Security & privacy

Local-first by design. Nothing is uploaded to any server run by this project.

| Data | Handling |
| --- | --- |
| Gemini API key | Environment variable, or `~/.translatedub/config.json` created `chmod 600` |
| Google Cloud service-account JSON | Same as above (env var or the config file) |
| Video / audio | Processed on your machine; temp files under `~/.translatedub/temp` |
| The local web server | Bound to `127.0.0.1` and rejects non-local requests |

Credential storage follows the same model as `gh`, `aws`, and `npm`: environment
variable first, then an owner-only file. See [SECURITY.md](SECURITY.md).

Supported credential environment variables:
`TRANSLATEDUB_GEMINI_KEY` (or `GEMINI_API_KEY`),
`TRANSLATEDUB_GOOGLE_CLOUD_CREDENTIALS` (or `GOOGLE_APPLICATION_CREDENTIALS` pointing to a JSON file).

## Develop

```bash
git clone https://github.com/Phong-EpicMind/video-translate-pro.git
cd video-translate-pro
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev,cloud]"
pytest
```

## License

MIT — see [LICENSE](LICENSE). Third-party components (FFmpeg, Google libraries, etc.)
are under their own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

---

<a id="tieng-viet"></a>

## Tiếng Việt

**TranslateDub AI** là công cụ dịch video, làm phụ đề song ngữ và lồng tiếng bằng AI,
chạy **cục bộ trên máy** (Mac/Windows/Linux). Video và API key **không rời khỏi máy bạn**.
Dùng được theo 3 cách: dòng lệnh (CLI), giao diện web (một lệnh mở trình duyệt), hoặc
thư viện Python.

### Cài đặt

Cần **Python 3.9+**. Không cần ký app, không cảnh báo tải về.

```bash
pipx install translatedub     # hoặc: pip install translatedub
```

FFmpeg tự lo: dùng `ffmpeg` hệ thống nếu có, không thì lấy bản đi kèm `imageio-ffmpeg`.

### Bắt đầu nhanh

```bash
translatedub config set-key                         # nhập Gemini API key (lưu file chmod 600)
translatedub translate input.mp4 --to vi -o out.mp4 # dịch + lồng tiếng một lệnh
translatedub serve                                  # hoặc mở giao diện web để sửa phụ đề
```

Lấy Gemini key miễn phí tại [Google AI Studio](https://aistudio.google.com/).

### Bảo mật

Chạy cục bộ, không upload lên server nào của dự án. Key lưu trong biến môi trường hoặc
file `~/.translatedub/config.json` với quyền `chmod 600` (giống cách `gh`, `aws`, `npm`
làm). Server web chỉ nhận kết nối từ `127.0.0.1`. Xem [SECURITY.md](SECURITY.md).

Đây là dự án độc lập, lấy cảm hứng từ quy trình tổng quát của
[pyVideoTrans](https://github.com/jianchang512/pyvideotrans); không copy/phụ thuộc
source code, asset hay binary của pyVideoTrans.

### Giấy phép

MIT — xem [LICENSE](LICENSE).
