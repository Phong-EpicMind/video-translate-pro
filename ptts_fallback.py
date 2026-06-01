from gtts import gTTS

def generate_gtts_voice(text: str, lang: str, output_path: str):
    """Fallback generator using the free gTTS library"""
    tts = gTTS(text=text, lang=lang)
    tts.save(output_path)
