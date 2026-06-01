# Contributing

Thanks for helping improve TranslateDub AI.

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

* Keep secrets out of the repository. Do not commit API keys, service account JSON, generated videos, temporary audio, `.dmg`, `.app`, `dist/`, `build/`, or `bin/`.
* Run the compile check above.
* Keep changes scoped. Avoid unrelated formatting churn.
* Update `README.md`, `THIRD_PARTY_NOTICES.md`, or `FFMPEG_SOURCE_OFFER.md` when changing packaging, bundled binaries, or licensing behavior.
* For binary releases containing FFmpeg/FFprobe, provide the corresponding FFmpeg source archive or a valid written source offer.

## Legal and Attribution Notes

TranslateDub AI source code is MIT licensed. Packaged releases may contain third-party components under other licenses, including GPL-3.0 FFmpeg/FFprobe binaries. Do not remove or weaken the third-party notices.

pyVideoTrans is credited as inspiration only. This project must not import, vendor, copy, or depend on pyVideoTrans source code, assets, or binaries unless the licensing model is explicitly revisited.
