import json
import os
from google.cloud import texttospeech
from google.oauth2 import service_account

def test_tts():
    config_path = "/Users/phongho/Master Project/Antigravity 2/video-translate-pro/config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
        
    credentials_json = config.get("google_cloud_credentials")
    if not credentials_json:
        print("Error: No credentials in config.json")
        return
        
    try:
        info = json.loads(credentials_json)
        credentials = service_account.Credentials.from_service_account_info(info)
        client = texttospeech.TextToSpeechClient(credentials=credentials)
        
        input_text = texttospeech.SynthesisInput(text="Xin chào Việt Nam")
        voice = texttospeech.VoiceSelectionParams(
            language_code="vi-VN",
            name="vi-VN-Neural2-A"
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        
        print("Attempting to synthesize speech...")
        response = client.synthesize_speech(
            input=input_text, voice=voice, audio_config=audio_config
        )
        print("Success! Synthesized audio size:", len(response.audio_content))
    except Exception as e:
        print("EXCEPTION ENCOUNTERED:")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_tts()
