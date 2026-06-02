# Third-Party Software Notices & Licenses

This document contains licensing and copyright notices for third-party software components included in or referenced by **TranslateDub AI**.

Tiếng Việt: Tài liệu này ghi nhận license và copyright của các thành phần bên thứ ba được sử dụng hoặc được tham chiếu bởi **TranslateDub AI**. Phần tiếng Anh dưới đây là thông báo pháp lý chính; phần tiếng Việt ở cuối file tóm tắt các điểm quan trọng cho người dùng Việt Nam.

---

## 1. FFmpeg and FFprobe (Bundled Binaries)

The distributed standalone macOS `.dmg` package of TranslateDub AI bundles pre-compiled static binary executables of **FFmpeg** and **FFprobe** to provide out-of-the-box audio and video processing capabilities.

* **License:** GNU General Public License v3.0 (GPL-3.0)
* **Copyright:** Copyright (c) 2000-2026 the FFmpeg developers
* **Bundled Version:** `N-124530-gf435ce22e1-https://www.martin-riedl.de`
* **Build Configuration:** The bundled binaries report `--enable-gpl --enable-version3` and are therefore treated as GPL-3.0 binaries.
* **Upstream Source Code:** FFmpeg source code is available from the official FFmpeg project at [ffmpeg.org](https://ffmpeg.org) and [git.ffmpeg.org/ffmpeg.git](https://git.ffmpeg.org/ffmpeg.git).
* **Exact Commit:** The bundled binaries identify FFmpeg commit `f435ce22e1`. A distributor of the `.dmg` should preserve this notice and provide Corresponding Source for that exact commit and build configuration.
* **Build Script:** The build script used to compile these static binaries is open-source and developed by Martin Riedl, available at [git.martin-riedl.de/ffmpeg/build-script](https://git.martin-riedl.de/ffmpeg/build-script).

For binary releases, include this notice with the `.dmg` and provide one of the GPL-compliant source access methods, such as a source archive attached to the same release or a written offer in the release notes. A suitable source archive name is `ffmpeg-N-124530-gf435ce22e1-corresponding-source.tar.xz`. See `FFMPEG_SOURCE_OFFER.md` for the release-maintainer checklist.

---

## 2. pyVideoTrans (Inspiration Attribution)

* **TranslateDub AI** is an independent, custom implementation inspired by the general workflow and concepts of **[pyVideoTrans](https://github.com/jianchang512/pyvideotrans)**.
* **Attribution Notice:** This repository does not contain any source code, assets, or binary files from the pyVideoTrans project, nor does it depend on it.
* **License:** pyVideoTrans is licensed under the GNU General Public License v3.0 (GPL-3.0). We highly respect and appreciate the creators of pyVideoTrans for their inspiring work.

---

## 3. Python Package Dependencies

TranslateDub AI utilizes several open-source libraries. Direct runtime dependencies declared by the source project include:

* **FastAPI** (MIT License) - Copyright (c) 2018 Sebastian Ramírez
* **Uvicorn** (BSD 3-Clause License) - Copyright (c) 2017-present, Encode-hosted developers
* **pywebview** (BSD 3-Clause License) - Copyright (c) 2014 Roman Sirokov
* **google-genai** (Apache License 2.0) - Copyright (c) 2025 Google LLC
* **google-cloud-texttospeech** (Apache License 2.0) - Copyright (c) 2018 Google LLC
* **gTTS** (MIT License) - Copyright (c) 2014 Pierre Nicolas Durette
* **pydub** (MIT License) - Copyright (c) 2011 James Robert
* **Jinja2** (BSD 3-Clause License) - Copyright (c) Pallets
* **python-multipart** (Apache License 2.0) - Copyright (c) Marcelo Trylesinski

The packaged `.app` may also include transitive Python dependencies selected by PyInstaller. License metadata and license files for bundled packages are preserved in the application bundle under `Contents/Resources/*.dist-info/` where available. Known bundled packages include:

* **cryptography** (Apache License 2.0 OR BSD 3-Clause License)
* **google-api-core** (Apache License 2.0)
* **MarkupSafe** (BSD 3-Clause License)
* **pydantic** (MIT License)
* **setuptools** (MIT License)
* **websockets** (BSD 3-Clause License)

When publishing a packaged `.dmg`, include this file, `FFMPEG_SOURCE_OFFER.md`, and the root `LICENSE` file in the release package so recipients can inspect both the TranslateDub AI source license and bundled third-party notices.

---

## Tóm tắt Tiếng Việt

* Source code riêng của TranslateDub AI được phát hành theo MIT License.
* Bản `.dmg` có bundle FFmpeg và FFprobe để xử lý audio/video. Hai binary này báo cáo `--enable-gpl --enable-version3`, vì vậy được đối xử như thành phần GPL-3.0.
* Khi phát hành `.dmg` có kèm FFmpeg/FFprobe, release phải kèm source archive tương ứng hoặc written source offer hợp lệ. Xem `FFMPEG_SOURCE_OFFER.md`.
* pyVideoTrans chỉ được ghi nhận là nguồn cảm hứng về workflow. Repo này không chứa source code, asset, hoặc binary của pyVideoTrans và không phụ thuộc vào pyVideoTrans.
* Các dependency Python có license riêng của chúng. Khi đóng gói release, cần giữ `LICENSE`, `THIRD_PARTY_NOTICES.md`, và `FFMPEG_SOURCE_OFFER.md` để người dùng có thể kiểm tra license.
