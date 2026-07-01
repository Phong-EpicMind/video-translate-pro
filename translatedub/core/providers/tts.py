"""Concrete TTS providers and the engine registry.

Free engines (edge, gtts) degrade gracefully via :func:`resolve_tts_provider`;
premium engines (google_cloud) fail loudly when unavailable so a deliberate
paid choice is never silently downgraded.

edge-tts is LGPLv3: it is an optional dependency invoked via its command-line
interface as a subprocess. It is never imported, vendored, or modified.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess

from .base import ProviderUnavailable

# Simple language code -> Google Cloud BCP-47 code.
_CLOUD_LANG = {
    "vi": "vi-VN", "en": "en-US", "zh": "cmn-CN", "ja": "ja-JP",
    "ko": "ko-KR", "fr": "fr-FR", "de": "de-DE", "es": "es-ES",
}

# Per-language default edge-tts neural voice.
_EDGE_LANG_DEFAULTS = {
    "vi": "vi-VN-HoaiMyNeural", "en": "en-US-AriaNeural", "zh": "zh-CN-XiaoxiaoNeural",
    "ja": "ja-JP-NanamiNeural", "ko": "ko-KR-SunHiNeural", "fr": "fr-FR-DeniseNeural",
    "de": "de-DE-KatjaNeural", "es": "es-ES-ElviraNeural",
}

_EDGE_CLI_CACHE: list = []


def _edge_cli() -> "str | None":
    """Resolve the edge-tts CLI on PATH, cached. None when not installed."""
    if not _EDGE_CLI_CACHE:
        _EDGE_CLI_CACHE.append(shutil.which("edge-tts"))
    return _EDGE_CLI_CACHE[0]


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


REGISTRY: dict = {
    p.name: p for p in (GTTSProvider(), EdgeTTSProvider(), GoogleCloudProvider())
}

# Free engines are tried in this order when a requested free engine is unavailable.
FREE_FALLBACK_ORDER = ("edge", "gtts")


def get_tts_provider(name: str):
    """Return the provider registered under ``name`` or raise ProviderUnavailable."""
    try:
        return REGISTRY[name]
    except KeyError:
        raise ProviderUnavailable(f"Unknown TTS engine: {name}")


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
