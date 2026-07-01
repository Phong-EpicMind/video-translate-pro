# Third-Party Software Notices & Licenses

This document records licensing and copyright notices for third-party software
components used or referenced by **TranslateDub AI**.

Tiếng Việt: Tài liệu này ghi nhận license của các thành phần bên thứ ba. Phần tiếng Anh
là thông báo pháp lý chính; phần tiếng Việt ở cuối tóm tắt các điểm quan trọng.

---

## 1. FFmpeg and FFprobe

TranslateDub AI does **not** bundle FFmpeg binaries in its Python distribution. FFmpeg
is provided at runtime by one of:

* A system-installed `ffmpeg` / `ffprobe` on the user's `PATH`, or
* The [`imageio-ffmpeg`](https://pypi.org/project/imageio-ffmpeg/) dependency, which
  downloads a per-platform static FFmpeg binary on first use.

FFmpeg is licensed under the LGPL-2.1+ or GPL-2+ depending on build configuration;
see [ffmpeg.org/legal.html](https://ffmpeg.org/legal.html). Because this project ships
no FFmpeg binaries of its own, no Corresponding Source obligation attaches to the
TranslateDub AI distribution. Users obtain FFmpeg under its own license terms from their
system package manager or via `imageio-ffmpeg`.

* **Copyright:** Copyright (c) 2000-2026 the FFmpeg developers.
* **Source:** [ffmpeg.org](https://ffmpeg.org), [git.ffmpeg.org/ffmpeg.git](https://git.ffmpeg.org/ffmpeg.git).

---

## 2. pyVideoTrans (Inspiration Attribution)

* **TranslateDub AI** is an independent implementation inspired by the general workflow
  and concepts of **[pyVideoTrans](https://github.com/jianchang512/pyvideotrans)**.
* This repository contains no source code, assets, or binaries from pyVideoTrans, and
  does not depend on it.
* pyVideoTrans is licensed under GPL-3.0. We respect and appreciate its creators.

---

## 3. Python Package Dependencies

Direct runtime dependencies declared in `pyproject.toml`:

* **FastAPI** (MIT) — Copyright (c) 2018 Sebastián Ramírez
* **Uvicorn** (BSD 3-Clause) — Copyright (c) 2017-present, Encode-hosted developers
* **Jinja2** (BSD 3-Clause) — Copyright (c) Pallets
* **python-multipart** (Apache-2.0) — Copyright (c) Marcelo Trylesinski
* **google-genai** (Apache-2.0) — Copyright (c) Google LLC
* **gTTS** (MIT) — Copyright (c) 2014 Pierre Nicolas Durette
* **pydub** (MIT) — Copyright (c) 2011 James Robert
* **imageio-ffmpeg** (BSD 2-Clause) — Copyright (c) 2018 imageio contributors

Optional dependency (`translatedub[cloud]`):

* **google-cloud-texttospeech** (Apache-2.0) — Copyright (c) Google LLC

Each dependency is distributed under its own license; refer to each project for full terms.

---

## Tóm tắt Tiếng Việt

* Source code của TranslateDub AI phát hành theo MIT License.
* Dự án **không bundle** binary FFmpeg. FFmpeg đến từ hệ thống của người dùng hoặc từ
  gói `imageio-ffmpeg` (tự tải khi dùng), theo license riêng của FFmpeg. Vì không phát
  hành binary FFmpeg nào, dự án không phát sinh nghĩa vụ cung cấp Corresponding Source.
* pyVideoTrans chỉ được ghi nhận là nguồn cảm hứng về workflow; repo không chứa và không
  phụ thuộc source/asset/binary của pyVideoTrans.
* Các dependency Python có license riêng của chúng.
