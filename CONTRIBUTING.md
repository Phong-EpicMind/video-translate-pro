# Contributing

Thanks for helping improve TranslateDub AI. This project values focused, security-conscious changes that keep the macOS app reliable for creators.

## Development Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m compileall -q app.py desktop.py utils.py ptts_fallback.py scratch
```

Install FFmpeg locally for development:

```bash
brew install ffmpeg
```

## Pull Request Standard

Before opening a pull request:

* Keep secrets out of the repository. Do not commit API keys, service account JSON, generated videos, temporary audio, `.dmg`, `.app`, `dist/`, `build/`, `bin/`, or `config.json`.
* Run the compile check above.
* Keep changes scoped. Avoid unrelated formatting churn.
* Update `README.md`, `THIRD_PARTY_NOTICES.md`, or `FFMPEG_SOURCE_OFFER.md` when changing packaging, bundled binaries, licensing behavior, or user-facing release instructions.
* For binary releases containing FFmpeg/FFprobe, provide the corresponding FFmpeg source archive or a valid written source offer.

## Legal And Attribution Notes

TranslateDub AI source code is MIT licensed. Packaged releases may contain third-party components under other licenses, including GPL-3.0 FFmpeg/FFprobe binaries. Do not remove or weaken the third-party notices.

pyVideoTrans is credited as inspiration only. This project must not import, vendor, copy, or depend on pyVideoTrans source code, assets, or binaries unless the licensing model is explicitly revisited.

---

## Tiếng Việt

Cảm ơn bạn đã đóng góp cho TranslateDub AI. Dự án ưu tiên các thay đổi gọn, có kiểm tra, và không làm yếu phần bảo mật của ứng dụng macOS.

### Cài đặt môi trường phát triển

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m compileall -q app.py desktop.py utils.py ptts_fallback.py scratch
```

Cài FFmpeg cho môi trường dev:

```bash
brew install ffmpeg
```

### Tiêu chuẩn Pull Request

Trước khi mở PR:

* Không commit secret. Không đưa API key, Service Account JSON, video/audio tạm, `.dmg`, `.app`, `dist/`, `build/`, `bin/`, hoặc `config.json` vào repo.
* Chạy compile check ở trên.
* Giữ thay đổi đúng phạm vi. Không format/refactor ngoài lề nếu không cần.
* Cập nhật `README.md`, `THIRD_PARTY_NOTICES.md`, hoặc `FFMPEG_SOURCE_OFFER.md` nếu thay đổi cách đóng gói, binary bundle, license, hoặc hướng dẫn release.
* Nếu release binary có kèm FFmpeg/FFprobe, phải kèm source archive tương ứng hoặc written source offer hợp lệ.

### Pháp lý và ghi nhận

Source code của TranslateDub AI dùng MIT License. Bản đóng gói có thể kèm thành phần bên thứ ba theo license riêng, gồm FFmpeg/FFprobe GPL-3.0. Không xóa hoặc làm yếu các third-party notices.

pyVideoTrans chỉ được ghi nhận là nguồn cảm hứng. Dự án này không được import, vendor, copy, hoặc phụ thuộc source code, asset, hay binary của pyVideoTrans nếu chưa xem lại rõ mô hình license.
