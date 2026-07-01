# Pluggable Engines — Phase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a pluggable TTS provider seam and make edge-tts the default free neural voice (Vietnamese included), with gTTS as graceful fallback and Google Cloud unchanged as premium.

**Architecture:** A new `translatedub/core/providers/` package defines a `TTSProvider` protocol and a registry of concrete providers (gTTS, edge-tts, Google Cloud). `core/tts.py`'s `synthesize_segment` stays the duration-matching orchestrator but delegates raw synthesis to the resolved provider. Free engines degrade gracefully; premium engines fail loudly. edge-tts is an optional dependency invoked via its CLI (never imported/vendored).

**Tech Stack:** Python 3.9+, pytest (mock all externals — no network, no ffmpeg), edge-tts CLI (LGPLv3, optional), gTTS, google-cloud-texttospeech.

## Global Constraints

- Python floor **>=3.9** (use `from __future__ import annotations`; `tuple[bool, str]` in annotations only).
- **No new required dependency.** edge-tts goes in the `[free]` extra only. Base install stays light.
- **edge-tts: call the CLI via subprocess; never `import edge_tts`; never vendor/modify** (LGPLv3).
- `public_config()` must expose **no secret values** — only presence flags and non-secret metadata.
- Preserve the web SSE/JSON contract; config payload may gain **additive** fields only.
- Keep existing duration-matching constants: `MIN_SPEED=0.8`, `MAX_SPEED=1.25`, `SPEED_TOLERANCE=1.05`.
- Every task ends green: `pytest -q`, `ruff check translatedub tests`, `bandit -r translatedub -ll`.
- Default Vietnamese voice: `vi-VN-HoaiMyNeural`; alternate `vi-VN-NamMinhNeural`.

## File Structure

- Create `translatedub/core/providers/__init__.py` — exports the TTS registry API.
- Create `translatedub/core/providers/base.py` — `TTSProvider` protocol + `ProviderUnavailable`.
- Create `translatedub/core/providers/tts.py` — `GTTSProvider`, `EdgeTTSProvider`, `GoogleCloudProvider`, `REGISTRY`, `get_tts_provider`, `resolve_tts_provider`, `available_tts_engines`.
- Modify `translatedub/core/tts.py` — `synthesize_segment` delegates to a resolved provider.
- Modify `translatedub/config.py` — default `tts_engine="edge"`; `public_config` adds `tts_engines`.
- Modify `translatedub/cli.py` — `--engine` gains `edge`.
- Modify `translatedub/web/server.py` — `ConfigResponse`/config payload gains `tts_engines`.
- Modify `translatedub/web/templates/index.html` + `static/js/main.js` — edge option + Vietnamese voice list.
- Modify `pyproject.toml` — add `free = ["edge-tts>=6"]`.
- Modify `THIRD_PARTY_NOTICES.md`, `README.md` — attribute edge-tts, add first-run hint.
- Create `tests/test_providers_tts.py` — provider unit tests.

---

### Task 1: TTS provider seam (base + registry + gTTS/Cloud, behavior-preserving)

**Files:**
- Create: `translatedub/core/providers/__init__.py`
- Create: `translatedub/core/providers/base.py`
- Create: `translatedub/core/providers/tts.py`
- Modify: `translatedub/core/tts.py`
- Test: `tests/test_providers_tts.py`

**Interfaces:**
- Produces: `ProviderUnavailable(Exception)`; `TTSProvider` protocol with attrs `name: str`, `premium: bool`, `supports_native_rate: bool` and methods `is_available(voice_config: dict) -> tuple[bool, str]`, `default_voice(lang: str) -> str | None`, `synthesize(text, lang, output_path, voice_config, speaking_rate) -> None`; `REGISTRY: dict[str, TTSProvider]`; `get_tts_provider(name: str) -> TTSProvider`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_providers_tts.py
import pytest
from translatedub.core.providers.base import ProviderUnavailable
from translatedub.core.providers import tts as prov


def test_registry_has_expected_engines():
    assert set(prov.REGISTRY) == {"gtts", "edge", "google_cloud"}


def test_get_known_provider_returns_instance():
    p = prov.get_tts_provider("gtts")
    assert p.name == "gtts"
    assert p.premium is False
    assert p.supports_native_rate is False


def test_get_unknown_provider_raises():
    with pytest.raises(ProviderUnavailable):
        prov.get_tts_provider("nope")


def test_cloud_provider_flags():
    p = prov.get_tts_provider("google_cloud")
    assert p.premium is True
    assert p.supports_native_rate is True


def test_gtts_provider_synthesize_calls_gtts(monkeypatch, tmp_path):
    calls = {}

    class FakeGTTS:
        def __init__(self, text, lang):
            calls["text"], calls["lang"] = text, lang

        def save(self, path):
            calls["path"] = path
            open(path, "wb").close()

    monkeypatch.setitem(__import__("sys").modules, "gtts", type("m", (), {"gTTS": FakeGTTS}))
    out = str(tmp_path / "o.mp3")
    prov.get_tts_provider("gtts").synthesize("hi", "vi", out, {}, 1.0)
    assert calls == {"text": "hi", "lang": "vi", "path": out}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_providers_tts.py -q`
Expected: FAIL with `ModuleNotFoundError: translatedub.core.providers`.

- [ ] **Step 3: Write minimal implementation**

```python
# translatedub/core/providers/base.py
"""Provider contract shared by pluggable pipeline engines."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


class ProviderUnavailable(Exception):
    """A requested engine cannot run in the current environment."""


@runtime_checkable
class TTSProvider(Protocol):
    name: str
    premium: bool
    supports_native_rate: bool

    def is_available(self, voice_config: dict) -> "tuple[bool, str]": ...

    def default_voice(self, lang: str) -> "str | None": ...

    def synthesize(self, text: str, lang: str, output_path: str,
                   voice_config: dict, speaking_rate: float) -> None: ...
```

```python
# translatedub/core/providers/tts.py
"""Concrete TTS providers and the engine registry."""
from __future__ import annotations

import json

from .base import ProviderUnavailable

# Simple language code -> Google Cloud BCP-47 code.
_CLOUD_LANG = {
    "vi": "vi-VN", "en": "en-US", "zh": "cmn-CN", "ja": "ja-JP",
    "ko": "ko-KR", "fr": "fr-FR", "de": "de-DE", "es": "es-ES",
}


class GTTSProvider:
    name = "gtts"
    premium = False
    supports_native_rate = False

    def is_available(self, voice_config: dict) -> "tuple[bool, str]":
        try:
            import gtts  # noqa: F401
        except ImportError:
            return False, "gTTS not installed"
        return True, ""

    def default_voice(self, lang: str) -> "str | None":
        return None

    def synthesize(self, text, lang, output_path, voice_config, speaking_rate) -> None:
        from gtts import gTTS

        gTTS(text=text, lang=lang).save(output_path)


class GoogleCloudProvider:
    name = "google_cloud"
    premium = True
    supports_native_rate = True

    def is_available(self, voice_config: dict) -> "tuple[bool, str]":
        if not voice_config.get("credentials_json"):
            return False, "Google Cloud credentials missing"
        try:
            import google.cloud.texttospeech  # noqa: F401
        except ImportError:
            return False, "google-cloud-texttospeech not installed (pip install translatedub[cloud])"
        return True, ""

    def default_voice(self, lang: str) -> "str | None":
        return None

    def synthesize(self, text, lang, output_path, voice_config, speaking_rate) -> None:
        from google.cloud import texttospeech

        creds_json = voice_config.get("credentials_json")
        if creds_json:
            from google.oauth2 import service_account

            info = json.loads(creds_json)
            creds = service_account.Credentials.from_service_account_info(info)
            client = texttospeech.TextToSpeechClient(credentials=creds)
        else:
            client = texttospeech.TextToSpeechClient()

        voice_name = voice_config.get("voice_name")
        if voice_name:
            language_code = "-".join(voice_name.split("-")[:2])
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code, name=voice_name
            )
        else:
            voice = texttospeech.VoiceSelectionParams(
                language_code=_CLOUD_LANG.get(lang, lang),
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
            )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=speaking_rate
        )
        response = client.synthesize_speech(
            input=texttospeech.SynthesisInput(text=text),
            voice=voice, audio_config=audio_config,
        )
        with open(output_path, "wb") as out:
            out.write(response.audio_content)


# EdgeTTSProvider is added in Task 2.
REGISTRY: "dict[str, object]" = {
    p.name: p for p in (GTTSProvider(), GoogleCloudProvider())
}


def get_tts_provider(name: str):
    try:
        return REGISTRY[name]
    except KeyError:
        raise ProviderUnavailable(f"Unknown TTS engine: {name}")
```

```python
# translatedub/core/providers/__init__.py
"""Pluggable pipeline engine providers."""
from .base import ProviderUnavailable, TTSProvider
from .tts import REGISTRY, get_tts_provider

__all__ = ["ProviderUnavailable", "TTSProvider", "REGISTRY", "get_tts_provider"]
```

Then rewire the orchestrator in `translatedub/core/tts.py`. Replace the private
`_synthesize_gtts`, `_cloud_client`, `_cloud_voice`, `_synthesize_cloud` helpers and the
engine `if/elif` in `synthesize_segment` with delegation (keep the module docstring,
`MIN_SPEED`/`MAX_SPEED`/`SPEED_TOLERANCE`, `_clamp`, and the `change_tempo`/`get_duration`
imports):

```python
# translatedub/core/tts.py  (synthesize_segment body, replacing the if/elif engine block)
from .providers.tts import get_tts_provider  # add to imports at top
...
def synthesize_segment(text, lang, engine, output_path, voice_config=None,
                       target_duration_ms=None, base_speed=1.0, match_duration=True,
                       log=None) -> bool:
    voice_config = voice_config or {}
    try:
        provider = get_tts_provider(engine)
        provider.synthesize(text, lang, output_path, voice_config, base_speed)

        if not os.path.exists(output_path):
            return False

        actual_ms = int(get_duration(output_path) * 1000)

        if match_duration and target_duration_ms and target_duration_ms > 0:
            if actual_ms > target_duration_ms * SPEED_TOLERANCE:
                ratio = min(actual_ms / target_duration_ms, MAX_SPEED)
                if provider.supports_native_rate:
                    provider.synthesize(
                        text, lang, output_path, voice_config, _clamp(base_speed * ratio)
                    )
                else:
                    speed = _clamp(base_speed * ratio)
                    if abs(speed - 1.0) > 0.01:
                        change_tempo(output_path, speed, log)
        elif not provider.supports_native_rate and abs(base_speed - 1.0) > 0.01:
            change_tempo(output_path, _clamp(base_speed), log)

        return True
    except Exception as exc:  # noqa: BLE001 - reported to caller via log
        if log:
            log(f"TTS error for '{text[:15]}...': {exc}")
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_providers_tts.py tests/test_tts.py -q`
Expected: PASS (new provider tests + existing TTS tests still green — behavior preserved).

- [ ] **Step 5: Commit**

```bash
git add translatedub/core/providers translatedub/core/tts.py tests/test_providers_tts.py
git commit -m "feat(tts): add provider seam; delegate synthesize_segment to registry"
```

---

### Task 2: EdgeTTSProvider (subprocess CLI) + Vietnamese voice defaults

**Files:**
- Modify: `translatedub/core/providers/tts.py`
- Test: `tests/test_providers_tts.py`

**Interfaces:**
- Consumes: `ProviderUnavailable`, `REGISTRY` from Task 1.
- Produces: `EdgeTTSProvider` with `name="edge"`, `premium=False`, `supports_native_rate=False`; `_EDGE_LANG_DEFAULTS` map; `edge` key added to `REGISTRY`; `_edge_cli() -> str | None` (cached PATH lookup).

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_providers_tts.py
def test_edge_in_registry_and_flags():
    p = prov.get_tts_provider("edge")
    assert p.name == "edge" and p.premium is False
    assert p.supports_native_rate is False


def test_edge_default_voice_vietnamese():
    assert prov.get_tts_provider("edge").default_voice("vi") == "vi-VN-HoaiMyNeural"
    assert prov.get_tts_provider("edge").default_voice("en") == "en-US-AriaNeural"


def test_edge_unavailable_when_cli_missing(monkeypatch):
    monkeypatch.setattr(prov, "_edge_cli", lambda: None)
    ok, reason = prov.get_tts_provider("edge").is_available({})
    assert ok is False and "translatedub[free]" in reason


def test_edge_synthesize_invokes_cli(monkeypatch, tmp_path):
    monkeypatch.setattr(prov, "_edge_cli", lambda: "/usr/bin/edge-tts")
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        # simulate the CLI writing the media file
        idx = cmd.index("--write-media") + 1
        open(cmd[idx], "wb").close()
        return type("R", (), {"returncode": 0, "stderr": ""})()

    monkeypatch.setattr(prov.subprocess, "run", fake_run)
    out = str(tmp_path / "o.mp3")
    prov.get_tts_provider("edge").synthesize("xin chào", "vi", out, {}, 1.0)
    cmd = seen["cmd"]
    assert cmd[0] == "/usr/bin/edge-tts"
    assert "--voice" in cmd and "vi-VN-HoaiMyNeural" in cmd
    assert "--text" in cmd and "xin chào" in cmd
    assert cmd[cmd.index("--write-media") + 1] == out


def test_edge_synthesize_missing_output_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(prov, "_edge_cli", lambda: "/usr/bin/edge-tts")

    def fake_run(cmd, **kw):
        return type("R", (), {"returncode": 1, "stderr": "boom"})()  # no file written

    monkeypatch.setattr(prov.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError):
        prov.get_tts_provider("edge").synthesize("hi", "vi", str(tmp_path / "x.mp3"), {}, 1.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_providers_tts.py -q -k edge`
Expected: FAIL (`edge` not in REGISTRY / `_edge_cli` undefined).

- [ ] **Step 3: Write minimal implementation**

Add to the top of `translatedub/core/providers/tts.py`:

```python
import os
import shutil
import subprocess

_EDGE_LANG_DEFAULTS = {
    "vi": "vi-VN-HoaiMyNeural", "en": "en-US-AriaNeural", "zh": "zh-CN-XiaoxiaoNeural",
    "ja": "ja-JP-NanamiNeural", "ko": "ko-KR-SunHiNeural", "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural", "es": "es-ES-ElviraNeural",
}

_EDGE_CLI_CACHE: "list" = []


def _edge_cli() -> "str | None":
    """Resolve the edge-tts CLI on PATH, cached. None when not installed."""
    if not _EDGE_CLI_CACHE:
        _EDGE_CLI_CACHE.append(shutil.which("edge-tts"))
    return _EDGE_CLI_CACHE[0]
```

Add the provider class (before `REGISTRY`):

```python
class EdgeTTSProvider:
    name = "edge"
    premium = False
    supports_native_rate = False

    def is_available(self, voice_config: dict) -> "tuple[bool, str]":
        if _edge_cli() is None:
            return False, "edge-tts not installed — pip install translatedub[free]"
        return True, ""

    def default_voice(self, lang: str) -> "str | None":
        return _EDGE_LANG_DEFAULTS.get(lang, _EDGE_LANG_DEFAULTS["en"])

    def synthesize(self, text, lang, output_path, voice_config, speaking_rate) -> None:
        cli = _edge_cli()
        if cli is None:
            raise RuntimeError("edge-tts CLI not found")
        voice = voice_config.get("voice_name") or self.default_voice(lang)
        cmd = [cli, "--voice", voice, "--text", text, "--write-media", output_path]
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if result.returncode != 0 or not os.path.exists(output_path):
            raise RuntimeError(f"edge-tts failed: {(result.stderr or '').strip()[:200]}")
```

Update the registry line to include edge:

```python
REGISTRY: "dict[str, object]" = {
    p.name: p for p in (GTTSProvider(), EdgeTTSProvider(), GoogleCloudProvider())
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_providers_tts.py -q`
Expected: PASS (all provider tests).

- [ ] **Step 5: Commit**

```bash
git add translatedub/core/providers/tts.py tests/test_providers_tts.py
git commit -m "feat(tts): add edge-tts provider via CLI subprocess"
```

---

### Task 3: Engine resolution/fallback + default engine = edge

**Files:**
- Modify: `translatedub/core/providers/tts.py`
- Modify: `translatedub/core/tts.py`
- Modify: `translatedub/config.py:19-27` (`DEFAULT_SETTINGS`)
- Test: `tests/test_providers_tts.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: `REGISTRY`, `get_tts_provider`, `ProviderUnavailable`.
- Produces: `FREE_FALLBACK_ORDER = ("edge", "gtts")`; `resolve_tts_provider(name, voice_config, log=None) -> TTSProvider`.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_providers_tts.py
def test_resolve_free_falls_back_with_log(monkeypatch):
    monkeypatch.setattr(prov, "_edge_cli", lambda: None)  # edge unavailable
    logs = []
    p = prov.resolve_tts_provider("edge", {}, log=logs.append)
    assert p.name == "gtts"
    assert any("translatedub[free]" in m for m in logs)


def test_resolve_premium_missing_creds_raises(monkeypatch):
    with pytest.raises(prov.ProviderUnavailable):
        prov.resolve_tts_provider("google_cloud", {}, log=None)  # no credentials_json


def test_resolve_available_returns_same(monkeypatch):
    monkeypatch.setattr(prov, "_edge_cli", lambda: "/usr/bin/edge-tts")
    assert prov.resolve_tts_provider("edge", {}).name == "edge"
```

```python
# add to tests/test_config.py
from translatedub import config


def test_default_tts_engine_is_edge():
    assert config.DEFAULT_SETTINGS["tts_engine"] == "edge"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_providers_tts.py tests/test_config.py -q -k "resolve or default_tts"`
Expected: FAIL (`resolve_tts_provider` undefined; default still `gtts`).

- [ ] **Step 3: Write minimal implementation**

Add to `translatedub/core/providers/tts.py`:

```python
FREE_FALLBACK_ORDER = ("edge", "gtts")


def resolve_tts_provider(name: str, voice_config: dict, log=None):
    """Resolve an engine, degrading free engines and failing loud on premium."""
    provider = get_tts_provider(name)
    ok, reason = provider.is_available(voice_config)
    if ok:
        return provider
    if not provider.premium:
        for alt in FREE_FALLBACK_ORDER:
            if alt == name:
                continue
            candidate = REGISTRY.get(alt)
            if candidate is None:
                continue
            alt_ok, _ = candidate.is_available(voice_config)
            if alt_ok:
                if log:
                    log(f"{name} unavailable ({reason}); using {alt}. "
                        f"For neural voices: pip install translatedub[free]")
                return candidate
    raise ProviderUnavailable(f"{name} unavailable: {reason}")
```

Export it in `translatedub/core/providers/__init__.py` (`resolve_tts_provider` added to the
`from .tts import ...` line and `__all__`).

In `translatedub/core/tts.py`, switch the orchestrator to resolve instead of hard get:

```python
# replace the import and the resolution line
from .providers.tts import resolve_tts_provider
...
        provider = resolve_tts_provider(engine, voice_config, log)
```

In `translatedub/config.py`, change the default:

```python
    "tts_engine": "edge",
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_providers_tts.py tests/test_config.py tests/test_tts.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add translatedub/core/providers translatedub/core/tts.py translatedub/config.py tests/
git commit -m "feat(tts): graceful free-engine fallback; default engine edge"
```

---

### Task 4: Surface engine availability in config + CLI

**Files:**
- Modify: `translatedub/core/providers/tts.py`
- Modify: `translatedub/config.py:136-142` (`public_config`)
- Modify: `translatedub/cli.py:127-128` (`--engine` choices)
- Modify: `translatedub/web/server.py` (config payload / `ConfigResponse`)
- Test: `tests/test_config.py`, `tests/test_web.py`

**Interfaces:**
- Consumes: `REGISTRY` from Task 1-2.
- Produces: `available_tts_engines(voice_config: dict | None = None) -> list[dict]` where each dict is `{"name": str, "available": bool, "premium": bool, "reason": str}`. `public_config()` result gains key `tts_engines` (that list).

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_config.py
def test_public_config_lists_engines_without_secrets(isolated_home):
    pub = config.public_config()
    names = {e["name"] for e in pub["tts_engines"]}
    assert {"gtts", "edge", "google_cloud"} <= names
    # never leak secret values
    assert "gemini_key" not in pub
    assert "google_cloud_credentials" not in pub
    for e in pub["tts_engines"]:
        assert set(e) == {"name", "available", "premium", "reason"}
```

```python
# add to tests/test_providers_tts.py
def test_available_tts_engines_shape(monkeypatch):
    monkeypatch.setattr(prov, "_edge_cli", lambda: None)
    engines = prov.available_tts_engines({})
    edge = next(e for e in engines if e["name"] == "edge")
    assert edge["available"] is False and edge["premium"] is False
    assert "translatedub[free]" in edge["reason"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py tests/test_providers_tts.py -q -k "engines"`
Expected: FAIL (`available_tts_engines` undefined; `tts_engines` missing).

- [ ] **Step 3: Write minimal implementation**

Add to `translatedub/core/providers/tts.py`:

```python
def available_tts_engines(voice_config: "dict | None" = None) -> "list[dict]":
    """Report each engine's current availability for UI/CLI (no secrets)."""
    vc = voice_config or {}
    out = []
    for name, provider in REGISTRY.items():
        ok, reason = provider.is_available(vc)
        out.append({
            "name": name, "available": ok,
            "premium": provider.premium, "reason": reason,
        })
    return out
```

In `translatedub/config.py`, extend `public_config` (import lazily to avoid a core→config
cycle: `core` must not import web/CLI, but `config` importing `core.providers` is fine
since providers do not import config):

```python
def public_config(config: dict | None = None) -> dict:
    from .core.providers.tts import available_tts_engines

    data = config if config is not None else load_config()
    result = {key: data.get(key, default) for key, default in DEFAULT_SETTINGS.items()}
    result["has_gemini_key"] = has_secret("gemini_key", data)
    result["has_google_cloud_credentials"] = has_secret("google_cloud_credentials", data)
    creds = get_secret("google_cloud_credentials", data)
    result["tts_engines"] = available_tts_engines({"credentials_json": creds})
    return result
```

In `translatedub/cli.py`, widen the choices:

```python
    t.add_argument("--engine", choices=("edge", "gtts", "google_cloud"), default="edge",
                   help="TTS engine (default: edge).")
```

In `translatedub/web/server.py`, if `ConfigResponse` enumerates fields, add
`tts_engines: list = []`; if it spreads `public_config()` into a dict response, no change
is needed beyond confirming the new key passes through. Verify the `/api/config` GET
returns `tts_engines`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py tests/test_web.py tests/test_providers_tts.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add translatedub/core/providers/tts.py translatedub/config.py translatedub/cli.py translatedub/web/server.py tests/
git commit -m "feat(tts): surface engine availability in config and CLI"
```

---

### Task 5: Web UI — edge option + Vietnamese voice list

**Files:**
- Modify: `translatedub/web/templates/index.html:53-56,116-118`
- Modify: `translatedub/web/static/js/main.js:66-77,203-210,543-551`
- Test: manual smoke (frontend has no unit harness); keep `tests/test_web.py` green.

**Interfaces:**
- Consumes: `/api/config` payload field `tts_engines` and existing `tts_engine`, `voice_name`.

- [ ] **Step 1: Add the edge option to the engine dropdown**

In `index.html`, add as the first `<option>` (default), keeping the others:

```html
<option value="edge" {% if config.tts_engine == 'edge' %}selected{% endif %}>Edge Neural (Miễn Phí - Giọng Tự Nhiên)</option>
```

- [ ] **Step 2: Show a Vietnamese voice list for edge**

In `main.js`, define edge voices and populate the voice selector when engine is `edge`
(reuse the existing `voiceNameGroup`/`voiceName` control). Near the `PREMIUM_VOICES`
definition add:

```javascript
const EDGE_VOICES = {
  vi: [
    { id: "vi-VN-HoaiMyNeural", label: "HoaiMy (Nữ)" },
    { id: "vi-VN-NamMinhNeural", label: "NamMinh (Nam)" },
  ],
};
```

In the function that populates voices (around line 66-77), branch on engine:

```javascript
function populateVoices(lang) {
  if (!voiceName) return;
  voiceName.innerHTML = "";
  const isEdge = ttsEngine.value === "edge";
  const source = isEdge ? (EDGE_VOICES[lang] || EDGE_VOICES["vi"])
                        : (PREMIUM_VOICES[lang] || PREMIUM_VOICES["vi"]);
  source.forEach(v => {
    const opt = document.createElement("option");
    opt.value = v.id || v;
    opt.textContent = v.label || v;
    voiceName.appendChild(opt);
  });
}
```

- [ ] **Step 3: Toggle the voice group for edge as well as cloud**

Around line 543-551 (the engine-change handler that shows/hides `voiceNameGroup`), make
both `edge` and `google_cloud` reveal it:

```javascript
if (ttsEngine.value === "google_cloud" || ttsEngine.value === "edge") {
  populateVoices(targetLang.value);
  voiceNameGroup.style.display = "block";
} else {
  voiceNameGroup.style.display = "none";
}
```

Update the engine-change listener (around line 203-210) to call the same logic so the list
refreshes when switching engines and when the target language changes.

- [ ] **Step 4: Manual smoke test**

Run: `translatedub serve --no-browser` then open `http://127.0.0.1:<port>`.
Expected: engine dropdown defaults to "Edge Neural"; selecting it shows the Vietnamese
voice list (HoaiMy default, NamMinh alternate). Also run `pytest tests/test_web.py -q`
(still green).

- [ ] **Step 5: Commit**

```bash
git add translatedub/web/templates/index.html translatedub/web/static/js/main.js
git commit -m "feat(ui): add edge engine and Vietnamese voice picker"
```

---

### Task 6: Packaging (`[free]` extra) + attribution + first-run hint

**Files:**
- Modify: `pyproject.toml:37-38`
- Modify: `THIRD_PARTY_NOTICES.md`
- Modify: `README.md`
- Test: `tests/test_config.py` (hint helper, if added) — otherwise doc-only.

**Interfaces:**
- Produces: extra `free`; optional helper `config.free_engine_hint() -> str` if a first-run
  message is wired into the CLI.

- [ ] **Step 1: Add the `[free]` extra**

In `pyproject.toml` under `[project.optional-dependencies]`:

```toml
free = ["edge-tts>=6"]
```

- [ ] **Step 2: Attribute edge-tts**

Append to `THIRD_PARTY_NOTICES.md`:

```markdown
## edge-tts

- License: LGPL-3.0-only
- Usage: optional dependency (extra `[free]`), invoked via its command-line interface as a
  subprocess. Not vendored, not modified. Provides free neural voices (including
  Vietnamese) through Microsoft Edge's online TTS service.
- Project: https://github.com/rany2/edge-tts
```

- [ ] **Step 3: Document the free voice in the README**

Add an install note near the existing install instructions:

```markdown
For free neural voices (recommended, includes Vietnamese):

    pip install "translatedub[free]"

Without it the app still works using gTTS. Premium Google Cloud voices: `pip install "translatedub[cloud]"` and add a key.
```

- [ ] **Step 4: Verify the build metadata**

Run: `python -c "import tomllib,pathlib; d=tomllib.loads(pathlib.Path('pyproject.toml').read_text()); assert 'edge-tts>=6' in d['project']['optional-dependencies']['free']; print('ok')"`
Expected: prints `ok`. Also `pip install -e ".[free]"` resolves (network-permitting).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml THIRD_PARTY_NOTICES.md README.md
git commit -m "build: add [free] extra with edge-tts; attribute and document"
```

---

## Final verification (after all tasks)

- [ ] `pytest -q` — all tests pass (no network, no ffmpeg needed).
- [ ] `ruff check translatedub tests` — clean.
- [ ] `bandit -r translatedub -ll` — clean (note `subprocess` use is argv-list, no shell).
- [ ] `translatedub config show` lists engine availability; `--engine edge` accepted.
- [ ] Update `CLAUDE.md` engine-roadmap row if wording drifted (edge-tts now the shipped default).
- [ ] Open a PR from `feature/pluggable-engines`; confirm CI matrix green before merge.

## Self-Review (completed by plan author)

- **Spec coverage:** A.1 provider abstraction → Task 1-2; A.2 orchestrator → Task 1; A.3
  default edge + optional → Task 3 + Task 6; A.4 fallback → Task 3; A.5 surfaced state →
  Task 4 (config/CLI) + Task 5 (UI); A.6 packaging/attribution → Task 6; A.7 error
  handling → Tasks 2-3; A.8 tests → each task's tests; A.9 done criteria → Final
  verification. No gaps.
- **Placeholder scan:** none — every code/test step shows concrete content.
- **Type consistency:** `resolve_tts_provider`, `get_tts_provider`, `available_tts_engines`,
  `_edge_cli`, `REGISTRY`, `FREE_FALLBACK_ORDER`, `ProviderUnavailable` used with identical
  names/signatures across tasks; provider attrs (`name`/`premium`/`supports_native_rate`)
  consistent throughout.
