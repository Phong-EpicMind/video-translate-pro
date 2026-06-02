# Release Checklist

Use this checklist before publishing a GitHub Release or making the repository public.

## Source Release

* Confirm `git status --short` is clean.
* Confirm no generated media, API keys, service account JSON, `.app`, `.dmg`, `dist/`, `build/`, `bin/`, `temp/`, `venv/`, `config.json`, or release artifacts are tracked.
* Run:

```bash
python -m compileall -q app.py desktop.py utils.py ptts_fallback.py scratch
python -m bandit -r app.py desktop.py utils.py ptts_fallback.py scratch -ll
```

## Packaged macOS Release

* Build with the README PyInstaller command so `LICENSE`, `THIRD_PARTY_NOTICES.md`, `FFMPEG_SOURCE_OFFER.md`, and bundled FFmpeg/FFprobe are included in the app bundle.
* Set `CFBundleIdentifier`, `CFBundleShortVersionString`, and `CFBundleVersion`.
* Verify bundled FFmpeg/FFprobe version:

```bash
dist/TranslateDub\ AI.app/Contents/Frameworks/bin/ffmpeg -version
dist/TranslateDub\ AI.app/Contents/Frameworks/bin/ffprobe -version
```

* Verify the app bundle signature:

```bash
codesign --verify --deep --strict --verbose=2 "dist/TranslateDub AI.app"
```

* Verify the `.dmg`:

```bash
hdiutil verify "release-artifacts/TranslateDub_AI_macOS_arm64_vX.Y.Z.dmg"
```

* Confirm the release bundle does not contain `config.json`, service account JSON, or secret-like files.
* If the `.dmg` contains FFmpeg/FFprobe binaries, attach the corresponding FFmpeg source archive to the same GitHub Release, or include a written source offer valid for at least three years.
* Attach `LICENSE`, `THIRD_PARTY_NOTICES.md`, `FFMPEG_SOURCE_OFFER.md`, `SHA256SUMS.txt`, and the FFmpeg corresponding source archive to the release.
* Do not advertise the app as endorsed by Google, pyVideoTrans, Apple, or any third-party service.
* State clearly whether the build is Apple Developer ID signed/notarized.

## Suggested Release Assets

* `TranslateDub_AI_macOS_arm64_vX.Y.Z.dmg`
* `SHA256SUMS.txt`
* `LICENSE`
* `THIRD_PARTY_NOTICES.md`
* `FFMPEG_SOURCE_OFFER.md`
* `ffmpeg-N-124530-gf435ce22e1-corresponding-source.tar.xz` when FFmpeg/FFprobe are bundled

---

## Tiếng Việt

Dùng checklist này trước khi publish GitHub Release hoặc public repo.

### Source release

* Xác nhận `git status --short` sạch.
* Xác nhận không track generated media, API key, Service Account JSON, `.app`, `.dmg`, `dist/`, `build/`, `bin/`, `temp/`, `venv/`, `config.json`, hoặc release artifacts.
* Chạy:

```bash
python -m compileall -q app.py desktop.py utils.py ptts_fallback.py scratch
python -m bandit -r app.py desktop.py utils.py ptts_fallback.py scratch -ll
```

### Bản đóng gói macOS

* Build theo lệnh PyInstaller trong README để app bundle có kèm `LICENSE`, `THIRD_PARTY_NOTICES.md`, `FFMPEG_SOURCE_OFFER.md`, và FFmpeg/FFprobe nếu bundle.
* Set `CFBundleIdentifier`, `CFBundleShortVersionString`, và `CFBundleVersion`.
* Kiểm tra version FFmpeg/FFprobe:

```bash
dist/TranslateDub\ AI.app/Contents/Frameworks/bin/ffmpeg -version
dist/TranslateDub\ AI.app/Contents/Frameworks/bin/ffprobe -version
```

* Kiểm tra code signature của app:

```bash
codesign --verify --deep --strict --verbose=2 "dist/TranslateDub AI.app"
```

* Kiểm tra file `.dmg`:

```bash
hdiutil verify "release-artifacts/TranslateDub_AI_macOS_arm64_vX.Y.Z.dmg"
```

* Xác nhận bundle release không có `config.json`, Service Account JSON, hoặc file giống secret.
* Nếu `.dmg` có kèm FFmpeg/FFprobe, phải attach FFmpeg source archive tương ứng vào cùng GitHub Release, hoặc có written source offer hợp lệ ít nhất 3 năm.
* Attach `LICENSE`, `THIRD_PARTY_NOTICES.md`, `FFMPEG_SOURCE_OFFER.md`, `SHA256SUMS.txt`, và FFmpeg corresponding source archive vào release.
* Không quảng cáo app như được Google, pyVideoTrans, Apple, hoặc dịch vụ bên thứ ba nào endorse.
* Nói rõ build đã Apple Developer ID signed/notarized hay chưa.
