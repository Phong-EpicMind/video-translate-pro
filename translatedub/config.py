"""Cross-platform configuration and credential storage.

Secrets are resolved from environment variables first, then from a per-user
JSON file created with owner-only permissions (``0o600``) — the same approach
used by ``gh``, ``aws`` and ``npm``. No system keychain, no code signing.

On-disk secrets are plaintext by design: encrypting a local file without a user
passphrase is obfuscation, not security. A future opt-in passphrase mode may add
real encryption.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

# Non-secret settings surfaced to the web UI, with defaults.
DEFAULT_SETTINGS = {
    "src_lang": "auto",
    "target_lang": "vi",
    "tts_engine": "gtts",
    "voice_name": "",
    "base_speed": 1.0,
    "match_duration": True,
    "output_dir": "",
}

SECRET_KEYS = ("gemini_key", "google_cloud_credentials")

# Environment overrides (checked in order) per secret.
_ENV_OVERRIDES = {
    "gemini_key": ("TRANSLATEDUB_GEMINI_KEY", "GEMINI_API_KEY"),
    "google_cloud_credentials": ("TRANSLATEDUB_GOOGLE_CLOUD_CREDENTIALS",),
}


def config_dir() -> Path:
    override = os.environ.get("TRANSLATEDUB_HOME")
    base = Path(override) if override else Path.home() / ".translatedub"
    return base


def config_file() -> Path:
    return config_dir() / "config.json"


def temp_dir() -> Path:
    return config_dir() / "temp"


def ensure_dirs() -> None:
    d = config_dir()
    d.mkdir(parents=True, exist_ok=True)
    temp_dir().mkdir(parents=True, exist_ok=True)
    _chmod(d, 0o700)
    _chmod(temp_dir(), 0o700)
    if config_file().exists():
        _chmod(config_file(), 0o600)


def _chmod(path: Path, mode: int) -> None:
    """Best-effort chmod. No-op semantics on Windows where POSIX modes don't apply."""
    if os.name == "nt":
        return
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def load_config() -> dict:
    path = config_file()
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def save_config(data: dict) -> bool:
    ensure_dirs()
    path = config_file()
    try:
        # Write with owner-only permissions from creation.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        _chmod(path, 0o600)
        return True
    except OSError:
        return False


def _env_secret(name: str) -> str:
    for env_name in _ENV_OVERRIDES.get(name, ()):
        value = os.environ.get(env_name)
        if value:
            return value
    # GOOGLE_APPLICATION_CREDENTIALS points to a JSON file on disk.
    if name == "google_cloud_credentials":
        path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if path and os.path.isfile(path):
            try:
                return Path(path).read_text(encoding="utf-8")
            except OSError:
                return ""
    return ""


def get_secret(name: str, config: dict | None = None) -> str:
    """Resolve a secret: environment variable first, then the config file."""
    if name not in SECRET_KEYS:
        raise KeyError(name)
    env_value = _env_secret(name)
    if env_value:
        return env_value
    data = config if config is not None else load_config()
    return str(data.get(name) or "")


def set_secret(name: str, value: str) -> None:
    if name not in SECRET_KEYS:
        raise KeyError(name)
    data = load_config()
    data[name] = value
    save_config(data)


def has_secret(name: str, config: dict | None = None) -> bool:
    return bool(get_secret(name, config))


def public_config(config: dict | None = None) -> dict:
    """Settings safe to expose to the UI: no secret values, only presence flags."""
    data = config if config is not None else load_config()
    result = {key: data.get(key, default) for key, default in DEFAULT_SETTINGS.items()}
    result["has_gemini_key"] = has_secret("gemini_key", data)
    result["has_google_cloud_credentials"] = has_secret("google_cloud_credentials", data)
    return result


def update_settings(updates: dict) -> dict:
    """Apply non-secret setting updates and persist. Returns public config."""
    data = load_config()
    for key, value in updates.items():
        if key in SECRET_KEYS:
            if value:
                data[key] = value
        elif key in DEFAULT_SETTINGS:
            data[key] = value
    save_config(data)
    return public_config(data)
