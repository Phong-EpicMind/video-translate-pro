# Contributing

Thanks for helping improve TranslateDub AI. This project values focused,
security-conscious changes that keep the cross-platform tool reliable.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev,cloud]"
pytest
```

FFmpeg is resolved automatically (system binary or `imageio-ffmpeg`). To use a system
build during development: `brew install ffmpeg` / `apt install ffmpeg` / `winget install ffmpeg`.

## Pull request standard

Before opening a pull request:

* Keep secrets out of the repository. Never commit API keys, service-account JSON,
  generated media, temporary audio/video, or `config.json`.
* Run `pytest` (and `bandit -r translatedub -ll`) and keep them green.
* Add or update tests for the behavior you change. Pure logic must stay unit-tested.
* Keep changes scoped. Avoid unrelated formatting churn.
* Update `README.md` and `THIRD_PARTY_NOTICES.md` when changing packaging, dependencies,
  licensing behavior, or user-facing commands.

## Legal and attribution

TranslateDub AI source code is MIT licensed. Do not remove or weaken the third-party
notices. FFmpeg is not bundled by this project; it is provided by the system or by the
`imageio-ffmpeg` dependency under its own license.

pyVideoTrans is credited as inspiration only. This project must not import, vendor,
copy, or depend on pyVideoTrans source code, assets, or binaries.

---

## Tiếng Việt

Cảm ơn bạn đã đóng góp cho TranslateDub AI. Dự án ưu tiên thay đổi gọn, có kiểm tra, và
không làm yếu phần bảo mật.

### Cài đặt môi trường

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev,cloud]"
pytest
```

FFmpeg tự lo (binary hệ thống hoặc `imageio-ffmpeg`).

### Tiêu chuẩn Pull Request

* Không commit secret (API key, service-account JSON, media, `config.json`).
* Chạy `pytest` và `bandit -r translatedub -ll`, giữ xanh.
* Thêm/cập nhật test cho phần bạn đổi. Logic thuần phải có unit test.
* Giữ thay đổi đúng phạm vi.
* Cập nhật `README.md`, `THIRD_PARTY_NOTICES.md` khi đổi đóng gói/dependency/license/lệnh.

### Pháp lý

Source code MIT. Dự án không bundle FFmpeg. pyVideoTrans chỉ là nguồn cảm hứng; không
import/vendor/copy/phụ thuộc.
