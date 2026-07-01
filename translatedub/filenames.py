"""Filesystem-safe filename helpers (Unicode-preserving)."""

from __future__ import annotations

import os
import re
import uuid


def sanitize_stem(filename: str) -> str:
    """Return a readable, filesystem-safe stem, preserving Unicode letters."""
    raw = os.path.splitext(os.path.basename(filename or ""))[0].strip()
    safe = re.sub(r"[^\w.\- ()]+", "_", raw, flags=re.UNICODE)
    safe = re.sub(r"_+", "_", safe).strip(" ._-")
    return (safe or "video")[:90]


def unique_path(directory: str, filename: str) -> str:
    """Return a path in ``directory`` that does not collide with an existing file."""
    path = os.path.join(directory, filename)
    if not os.path.exists(path):
        return path
    stem, ext = os.path.splitext(filename)
    for counter in range(2, 1000):
        candidate = os.path.join(directory, f"{stem}_{counter}{ext}")
        if not os.path.exists(candidate):
            return candidate
    return os.path.join(directory, f"{stem}_{uuid.uuid4().hex[:8]}{ext}")
