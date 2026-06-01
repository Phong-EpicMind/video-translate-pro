# Release Checklist

Use this checklist before publishing a GitHub Release or making the repository public.

## Source Release

* Confirm `git status --short` is clean.
* Confirm no generated media, API keys, service account JSON, `.app`, `.dmg`, `dist/`, `build/`, `bin/`, `temp/`, or `venv/` files are tracked.
* Run:

```bash
python -m compileall -q app.py desktop.py utils.py ptts_fallback.py scratch
```

## Packaged macOS Release

* Build with the README PyInstaller command so `LICENSE`, `THIRD_PARTY_NOTICES.md`, and `FFMPEG_SOURCE_OFFER.md` are included in the app bundle.
* Verify bundled FFmpeg/FFprobe version:

```bash
dist/TranslateDub\ AI.app/Contents/Frameworks/bin/ffmpeg -version
dist/TranslateDub\ AI.app/Contents/Frameworks/bin/ffprobe -version
```

* If the `.dmg` contains FFmpeg/FFprobe binaries, attach the corresponding FFmpeg source archive to the same GitHub Release, or include a written source offer valid for at least three years.
* Attach `THIRD_PARTY_NOTICES.md` and `FFMPEG_SOURCE_OFFER.md` to the release notes or release assets.
* Do not advertise the app as endorsed by Google or pyVideoTrans.

## Suggested Release Assets

* `TranslateDub_AI_macOS.dmg`
* `THIRD_PARTY_NOTICES.md`
* `FFMPEG_SOURCE_OFFER.md`
* `ffmpeg-N-124530-gf435ce22e1-corresponding-source.tar.xz` when FFmpeg/FFprobe are bundled
