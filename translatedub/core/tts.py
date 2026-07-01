"""Text-to-speech synthesis: free gTTS and premium Google Cloud TTS.

Both engines can optionally match a target subtitle duration: gTTS via ffmpeg
``atempo``, Google Cloud by re-synthesising at an adjusted speaking rate.
"""

from __future__ import annotations

import json
import os
from typing import Callable

from .media import change_tempo, get_duration

LogCallback = Callable[[str], None]

MIN_SPEED = 0.8
MAX_SPEED = 1.25
SPEED_TOLERANCE = 1.05  # only speed up when >5% over the target window

# Simple language code -> Google Cloud BCP-47 code.
_CLOUD_LANG = {
    "vi": "vi-VN", "en": "en-US", "zh": "cmn-CN", "ja": "ja-JP",
    "ko": "ko-KR", "fr": "fr-FR", "de": "de-DE", "es": "es-ES",
}


def _clamp(value: float, low: float = MIN_SPEED, high: float = MAX_SPEED) -> float:
    return max(low, min(high, value))


def _synthesize_gtts(text: str, lang: str, output_path: str) -> None:
    from gtts import gTTS

    gTTS(text=text, lang=lang).save(output_path)


def _cloud_client(credentials_json: str | None):
    from google.cloud import texttospeech

    if credentials_json:
        from google.oauth2 import service_account

        info = json.loads(credentials_json)
        creds = service_account.Credentials.from_service_account_info(info)
        return texttospeech.TextToSpeechClient(credentials=creds)
    return texttospeech.TextToSpeechClient()


def _cloud_voice(lang: str, voice_name: str | None):
    from google.cloud import texttospeech

    if voice_name:
        language_code = "-".join(voice_name.split("-")[:2])
        return texttospeech.VoiceSelectionParams(language_code=language_code, name=voice_name)
    return texttospeech.VoiceSelectionParams(
        language_code=_CLOUD_LANG.get(lang, lang),
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
    )


def _synthesize_cloud(text: str, lang: str, output_path: str, voice_config: dict,
                      speaking_rate: float) -> None:
    from google.cloud import texttospeech

    client = _cloud_client(voice_config.get("credentials_json"))
    voice = _cloud_voice(lang, voice_config.get("voice_name"))
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=speaking_rate
    )
    response = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text), voice=voice, audio_config=audio_config
    )
    with open(output_path, "wb") as out:
        out.write(response.audio_content)


def synthesize_segment(text: str, lang: str, engine: str, output_path: str,
                       voice_config: dict | None = None,
                       target_duration_ms: int | None = None,
                       base_speed: float = 1.0, match_duration: bool = True,
                       log: LogCallback | None = None) -> bool:
    """Synthesise one subtitle segment to ``output_path``. Returns success."""
    voice_config = voice_config or {}
    try:
        if engine == "gtts":
            _synthesize_gtts(text, lang, output_path)
        elif engine == "google_cloud":
            _synthesize_cloud(text, lang, output_path, voice_config, base_speed)
        else:
            return False

        if not os.path.exists(output_path):
            return False

        actual_ms = int(get_duration(output_path) * 1000)

        if match_duration and target_duration_ms and target_duration_ms > 0:
            if actual_ms > target_duration_ms * SPEED_TOLERANCE:
                ratio = min(actual_ms / target_duration_ms, MAX_SPEED)
                if engine == "google_cloud":
                    _synthesize_cloud(
                        text, lang, output_path, voice_config, _clamp(base_speed * ratio)
                    )
                else:
                    speed = _clamp(base_speed * ratio)
                    if abs(speed - 1.0) > 0.01:
                        change_tempo(output_path, speed, log)
        elif engine == "gtts" and abs(base_speed - 1.0) > 0.01:
            change_tempo(output_path, _clamp(base_speed), log)

        return True
    except Exception as exc:  # noqa: BLE001 - reported to caller via log
        if log:
            log(f"TTS error for '{text[:15]}...': {exc}")
        return False
