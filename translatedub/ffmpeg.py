"""Cross-platform resolution of the ffmpeg / ffprobe executables.

Resolution order:

1. An explicit override via the ``TRANSLATEDUB_FFMPEG`` / ``TRANSLATEDUB_FFPROBE``
   environment variables.
2. A binary found on ``PATH`` (``shutil.which``) or in common install locations.
3. For ffmpeg only: the static binary shipped by ``imageio-ffmpeg`` if installed.

``ffprobe`` may be unavailable (``imageio-ffmpeg`` ships only ffmpeg); callers must
handle a ``None`` return and fall back to ffmpeg-based probing.
"""

from __future__ import annotations

import os
import shutil
from functools import lru_cache

_COMMON_DIRS = (
    "/opt/homebrew/bin",
    "/usr/local/bin",
    "/usr/bin",
    "/bin",
)


def _from_common_dirs(name: str) -> str | None:
    for directory in _COMMON_DIRS:
        candidate = os.path.join(directory, name)
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


@lru_cache(maxsize=None)
def ffmpeg_path() -> str:
    """Return a usable ffmpeg path, raising ``RuntimeError`` if none is found."""
    override = os.environ.get("TRANSLATEDUB_FFMPEG")
    if override:
        return override

    found = shutil.which("ffmpeg") or _from_common_dirs("ffmpeg")
    if found:
        return found

    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass

    raise RuntimeError(
        "ffmpeg not found. Install it (brew/apt/winget install ffmpeg) or "
        "`pip install imageio-ffmpeg`."
    )


@lru_cache(maxsize=None)
def ffprobe_path() -> str | None:
    """Return a usable ffprobe path, or ``None`` if unavailable.

    ffprobe is optional: callers fall back to parsing ``ffmpeg -i`` output.
    """
    override = os.environ.get("TRANSLATEDUB_FFPROBE")
    if override:
        return override
    return shutil.which("ffprobe") or _from_common_dirs("ffprobe")


def reset_cache() -> None:
    """Clear cached resolutions (used by tests)."""
    ffmpeg_path.cache_clear()
    ffprobe_path.cache_clear()
