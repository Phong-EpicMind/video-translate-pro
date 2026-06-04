import os
import subprocess
import json
import re
from google import genai
from google.genai import types
from pydantic import BaseModel
from ptts_fallback import generate_gtts_voice # We will create a robust gTTS fallback helper

# Subtitle schemas for Pydantic (supported natively by google-genai structured output)
class SubtitleSegment(BaseModel):
    index: int
    start_ms: int
    end_ms: int
    original_text: str
    translated_text: str

class SubtitleList(BaseModel):
    subtitles: list[SubtitleSegment]

def ms_to_srt_time(ms: int) -> str:
    """Convert milliseconds to SRT timestamp format: HH:MM:SS,mmm"""
    hours = ms // 3600000
    minutes = (ms % 3600000) // 60000
    seconds = (ms % 60000) // 1000
    milliseconds = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def srt_time_to_ms(srt_time: str) -> int:
    """Convert SRT timestamp format HH:MM:SS,mmm to milliseconds"""
    match = re.match(r"(\d+):(\d+):(\d+),(\d+)", srt_time)
    if not match:
        return 0
    h, m, s, ms = map(int, match.groups())
    return h * 3600000 + m * 60000 + s * 1000 + ms

def get_clean_env() -> dict:
    """Get a copy of the current environment but restore original library paths if running under PyInstaller (sys.frozen)"""
    import sys
    env = os.environ.copy()
    if getattr(sys, 'frozen', False):
        # Restore original dynamic library paths if PyInstaller modified them
        for key in ['DYLD_LIBRARY_PATH', 'LD_LIBRARY_PATH', 'DYLD_FRAMEWORK_PATH']:
            orig_key = f"{key}_ORIG"
            if orig_key in env:
                env[key] = env[orig_key]
            else:
                env.pop(key, None)
    return env

def get_ffmpeg_path(executable_name="ffmpeg") -> str:
    """Find the path of the given executable (ffmpeg or ffprobe) on macOS, considering GUI app PATH limitations"""
    import sys
    
    # 1. Check if running under PyInstaller bundle and search the internal bin/ directory first
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        bundled_path = os.path.join(base_path, "bin", executable_name)
        if os.path.exists(bundled_path) and os.access(bundled_path, os.X_OK):
            return bundled_path

    # 2. Standard system fallback paths
    possible_paths = [
        f"/opt/homebrew/bin/{executable_name}",
        f"/usr/local/bin/{executable_name}",
        f"/usr/bin/{executable_name}",
        f"/bin/{executable_name}"
    ]
    for p in possible_paths:
        if os.path.exists(p) and os.access(p, os.X_OK):
            return p
            
    import shutil
    shutil_path = shutil.which(executable_name)
    if shutil_path:
        return shutil_path
        
    return executable_name

def get_media_duration(file_path: str) -> float:
    """Get the duration of a video or audio file in seconds using ffprobe"""
    cmd = [
        get_ffmpeg_path("ffprobe"), "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", file_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True, env=get_clean_env())
        return float(result.stdout.strip())
    except Exception as e:
        print(f"Error getting duration for {file_path}: {e}")
        return 0.0

def has_audio_stream(video_path: str) -> bool:
    """Check if a video file has an audio stream using ffprobe"""
    cmd = [
        get_ffmpeg_path("ffprobe"), "-v", "error", "-select_streams", "a",
        "-show_entries", "stream=codec_type", "-of", "default=nw=1:nk=1",
        video_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True, env=get_clean_env())
        return len(result.stdout.strip()) > 0
    except Exception as e:
        print(f"Error checking audio stream for {video_path}: {e}")
        return False

def extract_audio_from_video(video_path: str, audio_path: str, log_callback=None) -> bool:
    """Extract audio from video file using ffmpeg"""
    if log_callback:
        log_callback("Trích xuất âm thanh từ video...")
    
    cmd = [
        get_ffmpeg_path("ffmpeg"), "-y", "-i", video_path,
        "-vn", "-acodec", "libmp3lame", "-q:a", "2", "-ac", "1",
        audio_path
    ]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=get_clean_env())
        if result.returncode != 0:
            if log_callback:
                log_callback(f"Lỗi ffmpeg: {result.stderr}")
            return False
        if log_callback:
            log_callback("Trích xuất âm thanh thành công!")
        return True
    except Exception as e:
        if log_callback:
            log_callback(f"Lỗi trích xuất âm thanh: {e}")
        return False

def transcribe_and_translate_chunk(client: genai.Client, audio_chunk_path: str, src_lang: str, target_lang: str, offset_ms: int, chunk_index: int, log_callback=None) -> list[dict]:
    """Transcribe and translate a single audio chunk using Gemini with robust auto-retry and models fallback"""
    prompt = f"""You are a professional audio transcriber and translator.
Task:
1. Transcribe the provided audio file precisely.
2. Translate the transcribed text from '{src_lang}' to '{target_lang}'.
3. Break down the audio into subtitle segments. Each segment should represent a single sentence or coherent phrase, generally between 1 to 7 seconds long.
4. For each segment, output the start and end time in MILLISECONDS (integers) relative to the start of this audio clip.
5. Output the result strictly in the specified JSON schema.

Ensure timestamps are highly accurate and aligned with the actual speech in the audio.
"""

    models_to_try = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-2.0-flash-lite']
    max_retries_per_model = 2
    last_exception = None

    for model_name in models_to_try:
        for attempt in range(max_retries_per_model):
            audio_file = None
            try:
                if log_callback:
                    log_callback(f"Đang xử lý phân đoạn {chunk_index} bằng {model_name} (Lần thử {attempt + 1})...")
                
                # 1. Upload File
                audio_file = client.files.upload(file=audio_chunk_path)
                
                # 2. Generate Content
                response = client.models.generate_content(
                    model=model_name,
                    contents=[audio_file, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=SubtitleList,
                        temperature=0.0
                    ),
                )
                
                # 3. Clean up the uploaded file from Gemini storage immediately
                try:
                    client.files.delete(name=audio_file.name)
                except Exception as ex:
                    print(f"Error deleting file {audio_file.name}: {ex}")
                
                # 4. Parse response
                data = json.loads(response.text)
                subtitles = data.get("subtitles", [])
                
                # Apply offset and adjust indexes
                adjusted_subs = []
                for sub in subtitles:
                    adjusted_subs.append({
                        "index": len(adjusted_subs) + 1,
                        "start_ms": sub.get("start_ms", 0) + offset_ms,
                        "end_ms": sub.get("end_ms", 0) + offset_ms,
                        "original_text": sub.get("original_text", "").strip(),
                        "translated_text": sub.get("translated_text", "").strip()
                    })
                return adjusted_subs
                
            except Exception as e:
                last_exception = e
                err_msg = str(e)
                
                # Clean up file if it was created
                if audio_file:
                    try:
                        client.files.delete(name=audio_file.name)
                    except:
                        pass
                
                # Check if error is transient (503/429/Unavailable)
                is_transient = "503" in err_msg or "UNAVAILABLE" in err_msg or "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower()
                
                if is_transient:
                    wait_time = 3 * (attempt + 1)
                    if log_callback:
                        log_callback(f"⚠️ Máy chủ bận hoặc hết hạn mức (Lỗi {model_name}). Thử lại sau {wait_time} giây...")
                    import time
                    time.sleep(wait_time)
                else:
                    # Non-transient error (e.g. JSON schema, auth, etc.)
                    if log_callback:
                        log_callback(f"⚠️ Gặp lỗi với {model_name}: {err_msg[:120]}")
                    break # Break retry loop to try the next model
                    
    # If all models and retries failed, raise the last exception
    if last_exception:
        raise last_exception
    else:
        raise Exception("Không thể xử lý phân đoạn do lỗi dịch thuật.")

def transcribe_and_translate_audio(audio_path: str, gemini_key: str, src_lang: str, target_lang: str, log_callback=None) -> list[dict]:
    """Transcribe and translate audio file. Automatically chunks if file is long."""
    client = genai.Client(api_key=gemini_key)
    duration_sec = get_media_duration(audio_path)
    
    if duration_sec <= 0:
        if log_callback:
            log_callback("Không thể xác định độ dài file âm thanh.")
        return []
        
    if log_callback:
        log_callback(f"Độ dài file âm thanh: {duration_sec:.2f} giây.")

    # 10 minutes limit for a single chunk
    CHUNK_LIMIT_SEC = 600.0 
    
    if duration_sec <= CHUNK_LIMIT_SEC:
        # Process in one go
        subs = transcribe_and_translate_chunk(client, audio_path, src_lang, target_lang, 0, 1, log_callback)
        return subs
    else:
        # Split into 5-minute chunks (300 seconds)
        chunk_duration_sec = 300.0
        num_chunks = int(duration_sec // chunk_duration_sec) + (1 if duration_sec % chunk_duration_sec > 0 else 0)
        
        if log_callback:
            log_callback(f"Video dài ({duration_sec:.2f}s). Tự động chia làm {num_chunks} phân đoạn để xử lý chính xác...")
            
        all_subs = []
        for i in range(num_chunks):
            start_sec = i * chunk_duration_sec
            offset_ms = int(start_sec * 1000)
            
            # Temporary chunk file
            chunk_path = f"{os.path.splitext(audio_path)[0]}_chunk_{i}.mp3"
            
            if log_callback:
                log_callback(f"Cắt phân đoạn {i+1}/{num_chunks} (từ giây {start_sec:.1f})...")
                
            cmd = [
                get_ffmpeg_path("ffmpeg"), "-y", "-ss", str(start_sec), "-t", str(chunk_duration_sec),
                "-i", audio_path, "-acodec", "copy", chunk_path
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=get_clean_env())
            
            if not os.path.exists(chunk_path):
                if log_callback:
                    log_callback(f"Lỗi: Không thể cắt phân đoạn {i+1}")
                continue
                
            subs = transcribe_and_translate_chunk(client, chunk_path, src_lang, target_lang, offset_ms, i+1, log_callback)
            all_subs.extend(subs)
            
            # Clean up chunk file
            try:
                os.remove(chunk_path)
            except:
                pass
                
        # Re-index globally
        for index, sub in enumerate(all_subs):
            sub["index"] = index + 1
            
        return all_subs

def generate_tts_audio(
    text: str, 
    lang: str, 
    engine: str, 
    output_path: str, 
    voice_config: dict = None, 
    target_duration_ms: int = None, 
    base_speed: float = 1.0,
    match_duration: bool = True,
    log_callback=None
) -> bool:
    """Generate TTS audio for a single segment and automatically adjust speed naturally"""
    try:
        if engine == "gtts":
            # Call our gtts fallback
            generate_gtts_voice(text, lang, output_path)
        elif engine == "google_cloud":
            # Premium Google Cloud TTS
            from google.cloud import texttospeech
            from google.oauth2 import service_account
            
            credentials_json = voice_config.get("credentials_json") if voice_config else None
            voice_name = voice_config.get("voice_name") if voice_config else None
            
            if credentials_json:
                info = json.loads(credentials_json)
                credentials = service_account.Credentials.from_service_account_info(info)
                client = texttospeech.TextToSpeechClient(credentials=credentials)
            else:
                client = texttospeech.TextToSpeechClient()
                
            input_text = texttospeech.SynthesisInput(text=text)
            
            # Configure voice selection
            if voice_name:
                # Extract correct language code from voice name prefix, e.g. 'vi-VN-Neural2-A' -> 'vi-VN'
                actual_lang = "-".join(voice_name.split("-")[:2])
                voice = texttospeech.VoiceSelectionParams(
                    language_code=actual_lang,
                    name=voice_name
                )
            else:
                # Default selection: map simple 'vi' to 'vi-VN', etc.
                actual_lang = lang
                if lang == "vi": actual_lang = "vi-VN"
                elif lang == "en": actual_lang = "en-US"
                elif lang == "zh": actual_lang = "cmn-CN"
                elif lang == "ja": actual_lang = "ja-JP"
                elif lang == "ko": actual_lang = "ko-KR"
                elif lang == "fr": actual_lang = "fr-FR"
                elif lang == "de": actual_lang = "de-DE"
                elif lang == "es": actual_lang = "es-ES"
                voice = texttospeech.VoiceSelectionParams(
                    language_code=actual_lang,
                    ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
                )
                
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=base_speed
            )
            
            response = client.synthesize_speech(
                input=input_text, voice=voice, audio_config=audio_config
            )
            
            with open(output_path, "wb") as out:
                out.write(response.audio_content)
        else:
            return False
            
        if not os.path.exists(output_path):
            return False
            
        actual_duration = get_media_duration(output_path)
        actual_duration_ms = int(actual_duration * 1000)
        
        # Match duration if target is specified and enabled
        if match_duration and target_duration_ms and target_duration_ms > 0:
            # If the spoken audio is longer than the subtitle window by more than 5%
            if actual_duration_ms > target_duration_ms * 1.05:
                speed_ratio = actual_duration_ms / target_duration_ms
                
                # Cap speed-up to 1.25x to keep it completely natural and prevent robotic speed-ups
                if speed_ratio > 1.25:
                    speed_ratio = 1.25
                
                if engine == "google_cloud":
                    # For Google Cloud, re-synthesize at the exact speed ratio natively to keep premium quality!
                    target_speed = base_speed * speed_ratio
                    target_speed = max(0.8, min(1.25, target_speed))
                    
                    audio_config = texttospeech.AudioConfig(
                        audio_encoding=texttospeech.AudioEncoding.MP3,
                        speaking_rate=target_speed
                    )
                    
                    response = client.synthesize_speech(
                        input=input_text, voice=voice, audio_config=audio_config
                    )
                    
                    with open(output_path, "wb") as out:
                        out.write(response.audio_content)
                else:
                    # For gtts offline fallback, use ffmpeg atempo
                    final_speed = base_speed * speed_ratio
                    final_speed = max(0.8, min(1.25, final_speed))
                    
                    if abs(final_speed - 1.0) > 0.01:
                        temp_output = f"{os.path.splitext(output_path)[0]}_speed.mp3"
                        cmd = [
                            get_ffmpeg_path("ffmpeg"), "-y", "-i", output_path,
                            "-filter:a", f"atempo={final_speed:.2f}",
                            temp_output
                        ]
                        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=get_clean_env())
                        
                        if os.path.exists(temp_output):
                            os.replace(temp_output, output_path)
        else:
            # If match_duration is false, but user set a custom base speed for gtts
            if abs(base_speed - 1.0) > 0.01 and engine == "gtts":
                temp_output = f"{os.path.splitext(output_path)[0]}_speed.mp3"
                cmd = [
                    get_ffmpeg_path("ffmpeg"), "-y", "-i", output_path,
                    "-filter:a", f"atempo={base_speed:.2f}",
                    temp_output
                ]
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=get_clean_env())
                
                if os.path.exists(temp_output):
                    os.replace(temp_output, output_path)
                    
        return True
    except Exception as e:
        if log_callback:
            log_callback(f"Lỗi tạo TTS cho '{text[:15]}...': {e}")
        return False

def make_subtitles_srt(subtitles: list[dict], srt_path: str):
    """Write subtitle dictionary list into a standard SRT file"""
    with open(srt_path, "w", encoding="utf-8") as f:
        for sub in subtitles:
            index = sub.get("index")
            start = ms_to_srt_time(sub.get("start_ms"))
            end = ms_to_srt_time(sub.get("end_ms"))
            text = sub.get("translated_text", "")
            f.write(f"{index}\n{start} --> {end}\n{text}\n\n")

def _escape_subtitle_filter_path(srt_path: str) -> str:
    return srt_path.replace(":", "\\:").replace("'", "'\\''")

def export_subtitled_video(
    video_path: str,
    srt_path: str,
    output_path: str,
    burn_subtitles: bool = True,
    log_callback=None,
) -> bool:
    """Export the original video with translated subtitles but without generating a dubbed audio track."""
    if log_callback:
        mode_label = "phụ đề cứng" if burn_subtitles else "phụ đề mềm"
        log_callback(f"Đang tạo video chỉ có {mode_label}...")

    if burn_subtitles:
        escaped_srt = _escape_subtitle_filter_path(srt_path)
        cmd = [
            get_ffmpeg_path("ffmpeg"), "-y",
            "-i", video_path,
            "-vf", f"subtitles='{escaped_srt}'",
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "copy",
            output_path,
        ]
    else:
        cmd = [
            get_ffmpeg_path("ffmpeg"), "-y",
            "-i", video_path,
            "-i", srt_path,
            "-map", "0",
            "-map", "1:0",
            "-c", "copy",
            "-c:s", "mov_text",
            output_path,
        ]

    try:
        if log_callback:
            log_callback(f"Lệnh chạy: {' '.join(cmd)}")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=get_clean_env())
        if result.returncode != 0:
            if log_callback:
                log_callback(f"Lỗi xuất video phụ đề: {result.stderr}")
            return False
        if log_callback:
            log_callback("Hoàn thành xuất video phụ đề thành công!")
        return True
    except Exception as e:
        if log_callback:
            log_callback(f"Lỗi hệ thống khi xuất video phụ đề: {e}")
        return False

def merge_dubbed_audio_to_video(
    video_path: str, 
    dubbed_audio_path: str, 
    output_path: str, 
    original_vol: float, 
    dub_vol: float, 
    srt_path: str = None, 
    burn_subtitles: bool = False, 
    log_callback=None
) -> bool:
    """Combine dubbed audio and original video, handling audio mixing (ducking) and subtitles"""
    has_audio = has_audio_stream(video_path)
    
    if log_callback:
        log_callback("Đang tiến hành ghép âm thanh và video...")
        log_callback(f"Nhạc nền gốc: {original_vol*100:.0f}%, Âm lượng lồng tiếng: {dub_vol*100:.0f}%")
        
    cmd = [get_ffmpeg_path("ffmpeg"), "-y"]
    
    # All inputs must be declared first
    cmd.extend(["-i", video_path])
    cmd.extend(["-i", dubbed_audio_path])
    
    use_soft_sub = srt_path and os.path.exists(srt_path) and not burn_subtitles
    if use_soft_sub:
        cmd.extend(["-i", srt_path])
        
    filter_complex = []
    
    # Audio Mixing
    if has_audio and original_vol > 0:
        filter_complex.append(f"[0:a]volume={original_vol:.2f}[a0]; [1:a]volume={dub_vol:.2f}[a1]; [a0][a1]amix=inputs=2:duration=first[aout]")
        cmd.extend(["-filter_complex", ";".join(filter_complex)])
        cmd.extend(["-map", "0:v"])
        cmd.extend(["-map", "[aout]"])
    else:
        cmd.extend(["-filter_complex", f"[1:a]volume={dub_vol:.2f}[aout]"])
        cmd.extend(["-map", "0:v"])
        cmd.extend(["-map", "[aout]"])
        
    # Subtitle Processing
    if srt_path and os.path.exists(srt_path):
        if burn_subtitles:
            if log_callback:
                log_callback("Ghi phụ đề cứng (burn-in) vào video (cần thời gian mã hóa lại)...")
            escaped_srt = _escape_subtitle_filter_path(srt_path)
            cmd.extend(["-vf", f"subtitles='{escaped_srt}'"])
            cmd.extend(["-c:v", "libx264", "-preset", "fast"])
        else:
            if log_callback:
                log_callback("Nhúng phụ đề mềm (soft-sub) vào luồng phụ đề...")
            cmd.extend(["-map", "2:s?"]) # Map subtitle if available
            cmd.extend(["-c:v", "copy"])
            cmd.extend(["-c:s", "mov_text"])
    else:
        cmd.extend(["-c:v", "copy"])
        
    cmd.extend(["-c:a", "aac"])
    cmd.append(output_path) # Append output file at the end
    
    try:
        if log_callback:
            log_callback(f"Lệnh chạy: {' '.join(cmd)}")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=get_clean_env())
        if result.returncode != 0:
            if log_callback:
                log_callback(f"Lỗi ghép video: {result.stderr}")
            return False
        if log_callback:
            log_callback("Hoàn thành ghép video & âm thanh thành công!")
        return True
    except Exception as e:
        if log_callback:
            log_callback(f"Lỗi hệ thống khi ghép video: {e}")
        return False
