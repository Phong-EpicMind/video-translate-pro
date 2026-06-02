import os
import sys
import json
import asyncio
import uuid
import shutil

try:
    import Security
except Exception:
    Security = None

# Clean up PyInstaller dynamic library paths at startup so external subprocesses run in system environment
if getattr(sys, 'frozen', False):
    for key in ['DYLD_LIBRARY_PATH', 'LD_LIBRARY_PATH', 'DYLD_FRAMEWORK_PATH']:
        orig_key = f"{key}_ORIG"
        if orig_key in os.environ:
            os.environ[key] = os.environ[orig_key]
        else:
            os.environ.pop(key, None)

# Prepend Homebrew and standard system paths to PATH so child processes (including pydub) can find ffmpeg/ffprobe
homebrew_bin = "/opt/homebrew/bin"
local_bin = "/usr/local/bin"
current_path = os.environ.get("PATH", "")
path_parts = []
if os.path.exists(homebrew_bin):
    path_parts.append(homebrew_bin)
if os.path.exists(local_bin):
    path_parts.append(local_bin)
if current_path:
    path_parts.append(current_path)
if path_parts:
    os.environ["PATH"] = os.pathsep.join(path_parts)

from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional

import utils

app = FastAPI(title="Video Translate Pro")

LOCAL_CLIENT_HOSTS = {"127.0.0.1", "::1", "localhost"}
KEYCHAIN_SERVICE = "com.phongho.translatedubai"
SECRET_CONFIG_KEYS = {
    "gemini_key": "gemini_api_key",
    "google_cloud_credentials": "google_cloud_service_account_json",
}

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# standard writable user home folder for temp and config on macOS
USER_DATA_DIR = os.path.join(os.path.expanduser("~"), ".translatedub_ai")
TEMP_DIR = os.path.join(USER_DATA_DIR, "temp")
CONFIG_FILE = os.path.join(USER_DATA_DIR, "config.json")

os.makedirs(USER_DATA_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Enforce strict folder permissions: chmod 700 (owner read/write/execute only) for privacy
try:
    os.chmod(USER_DATA_DIR, 0o700)
    os.chmod(TEMP_DIR, 0o700)
    if os.path.exists(CONFIG_FILE):
        os.chmod(CONFIG_FILE, 0o600)
except Exception:
    pass

# Mount static files and templates
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/temp", StaticFiles(directory=TEMP_DIR), name="temp") # Allow streaming/downloading preview videos easily
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.middleware("http")
async def local_only_requests(request: Request, call_next):
    client_host = request.client.host if request.client else ""
    if client_host not in LOCAL_CLIENT_HOSTS:
        return JSONResponse(status_code=403, content={"detail": "Local access only."})
    return await call_next(request)

# Config Helpers
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_config(config_data):
    try:
        fd = os.open(CONFIG_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)

        # Enforce strict file permissions: chmod 600 (owner read/write only) to protect credentials
        try:
            os.chmod(CONFIG_FILE, 0o600)
        except Exception:
            pass
            
        return True
    except Exception:
        return False

def _keychain_query(account: str) -> dict:
    return {
        Security.kSecClass: Security.kSecClassGenericPassword,
        Security.kSecAttrService: KEYCHAIN_SERVICE,
        Security.kSecAttrAccount: account,
    }

def keychain_available() -> bool:
    return Security is not None

def keychain_get(account: str) -> str:
    if not keychain_available():
        return ""

    query = _keychain_query(account)
    query[Security.kSecReturnData] = True
    query[Security.kSecMatchLimit] = Security.kSecMatchLimitOne
    status, data = Security.SecItemCopyMatching(query, None)
    if status == Security.errSecItemNotFound:
        return ""
    if status != Security.errSecSuccess:
        raise RuntimeError(f"Keychain read failed with status {status}.")
    return bytes(data).decode("utf-8") if data is not None else ""

def keychain_set(account: str, value: str) -> None:
    if not keychain_available():
        raise RuntimeError("macOS Keychain is not available.")

    query = _keychain_query(account)
    encoded_value = value.encode("utf-8")
    status, _ = Security.SecItemAdd({**query, Security.kSecValueData: encoded_value}, None)
    if status == Security.errSecDuplicateItem:
        status = Security.SecItemUpdate(query, {Security.kSecValueData: encoded_value})
    if status != Security.errSecSuccess:
        raise RuntimeError(f"Keychain write failed with status {status}.")

def get_secret(config_key: str) -> str:
    return keychain_get(SECRET_CONFIG_KEYS[config_key])

def set_secret(config_key: str, value: str) -> None:
    keychain_set(SECRET_CONFIG_KEYS[config_key], value)

def redact_config_secrets(config_data: dict) -> dict:
    return {key: value for key, value in config_data.items() if key not in SECRET_CONFIG_KEYS}

def migrate_config_secrets_to_keychain(config_data: dict) -> dict:
    migrated = False
    for config_key in SECRET_CONFIG_KEYS:
        value = config_data.get(config_key)
        if value:
            set_secret(config_key, value)
            migrated = True

    if migrated:
        config_data = redact_config_secrets(config_data)
        save_config(config_data)
    return config_data

def public_config(config_data):
    """Return UI-safe settings without exposing stored credentials."""
    config_data = migrate_config_secrets_to_keychain(config_data)
    return {
        "has_gemini_key": bool(get_secret("gemini_key")),
        "has_google_cloud_credentials": bool(get_secret("google_cloud_credentials")),
        "src_lang": config_data.get("src_lang", "auto"),
        "target_lang": config_data.get("target_lang", "vi"),
        "tts_engine": config_data.get("tts_engine", "gtts"),
        "voice_name": config_data.get("voice_name", ""),
        "base_speed": config_data.get("base_speed", 1.0),
        "match_duration": config_data.get("match_duration", True),
        "output_dir": config_data.get("output_dir", ""),
    }

# Pydantic schemas for request payloads
class ConfigUpdate(BaseModel):
    gemini_key: Optional[str] = None
    google_cloud_credentials: Optional[str] = None
    src_lang: Optional[str] = "auto"
    target_lang: Optional[str] = "vi"
    tts_engine: Optional[str] = "gtts"
    voice_name: Optional[str] = ""
    base_speed: Optional[float] = 1.0
    match_duration: Optional[bool] = True
    output_dir: Optional[str] = ""

class SubtitleItem(BaseModel):
    index: int
    start_ms: int
    end_ms: int
    original_text: str
    translated_text: str

class DubbingRequest(BaseModel):
    video_path: str
    subtitles: List[SubtitleItem]
    original_vol: float
    dub_vol: float
    burn_subtitles: bool
    tts_engine: str # 'gtts' or 'google_cloud'
    voice_name: Optional[str] = ""
    base_speed: Optional[float] = 1.0
    match_duration: Optional[bool] = True

# Page routes
@app.get("/", response_class=HTMLResponse)
async def read_item(request: Request):
    config = public_config(load_config())
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"config": config}
    )

# API routes
@app.get("/api/config")
async def get_config():
    return JSONResponse(content=public_config(load_config()))

@app.post("/api/config")
async def update_config(data: ConfigUpdate):
    config = migrate_config_secrets_to_keychain(load_config())
    incoming = data.model_dump()
    for key, value in incoming.items():
        if key in {"gemini_key", "google_cloud_credentials"}:
            if value:
                set_secret(key, value)
            continue
        config[key] = value

    if not get_secret("gemini_key"):
        raise HTTPException(status_code=400, detail="Gemini API Key is required.")

    config = redact_config_secrets(config)
    if save_config(config):
        return {"status": "success", "message": "Lưu cài đặt thành công!", "config": public_config(config)}
    else:
        raise HTTPException(status_code=500, detail="Không thể lưu file cấu hình.")

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file to the temp directory"""
    try:
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"video_{uuid.uuid4().hex}{file_ext}"
        filepath = os.path.join(TEMP_DIR, unique_filename)
        
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {"status": "success", "video_path": filepath, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi tải video: {e}")

@app.get("/api/translate/progress")
async def translate_progress(video_path: str, src_lang: str, target_lang: str):
    """SSE endpoint to perform transcription & translation with live progress logs"""
    async def log_generator():
        # Validate inputs
        if not video_path or not os.path.exists(video_path):
            yield f"data: {json.dumps({'step': 'error', 'message': 'Không tìm thấy file video nguồn.'})}\n\n"
            return
            
        config = migrate_config_secrets_to_keychain(load_config())
        gemini_key = get_secret("gemini_key")
            
        if not gemini_key:
            yield f"data: {json.dumps({'step': 'error', 'message': 'Chưa nhập Gemini API Key.'})}\n\n"
            return
            
        video_filename = os.path.basename(video_path)
        audio_path = os.path.join(TEMP_DIR, f"{os.path.splitext(video_filename)[0]}.mp3")
        
        try:
            # 1. Init
            yield f"data: {json.dumps({'step': 'init', 'status': 'processing', 'message': 'Khởi chạy luồng dịch video...'})}\n\n"
            await asyncio.sleep(0.5)
            
            # 2. Extract Audio
            yield f"data: {json.dumps({'step': 'extract', 'status': 'processing', 'message': 'Bắt đầu trích xuất âm thanh bằng ffmpeg...'})}\n\n"
            
            extraction_logs = []
            def run_extraction():
                def callback(msg):
                    extraction_logs.append(msg)
                    print(f"[FFmpeg Extract] {msg}")
                return utils.extract_audio_from_video(video_path, audio_path, log_callback=callback)
                
            success = await asyncio.to_thread(run_extraction)
            
            for log in extraction_logs:
                yield f"data: {json.dumps({'step': 'extract', 'status': 'processing', 'message': log})}\n\n"
                await asyncio.sleep(0.05)
                
            if not success:
                last_err = extraction_logs[-1] if extraction_logs else "Lỗi không xác định."
                yield f"data: {json.dumps({'step': 'error', 'message': f'Không thể trích xuất âm thanh từ video: {last_err}'})}\n\n"
                return
                
            yield f"data: {json.dumps({'step': 'extract', 'status': 'done', 'message': 'Trích xuất âm thanh thành công!'})}\n\n"
            await asyncio.sleep(0.5)
            
            # 3. Transcribe & Translate
            yield f"data: {json.dumps({'step': 'transcribe', 'status': 'processing', 'message': 'Đang gửi âm thanh lên Google Gemini để nhận diện & dịch thuật...'})}\n\n"
            
            import queue
            import threading
            
            log_queue = queue.Queue()
            result_container = {"subtitles": None, "success": False, "error": None}
            
            def run_translation_thread():
                def callback(msg):
                    log_queue.put(msg)
                try:
                    res = utils.transcribe_and_translate_audio(
                        audio_path=audio_path,
                        gemini_key=gemini_key,
                        src_lang=src_lang,
                        target_lang=target_lang,
                        log_callback=callback
                    )
                    result_container["subtitles"] = res
                    result_container["success"] = True
                except Exception as ex:
                    result_container["error"] = str(ex)
                    result_container["success"] = False
                finally:
                    log_queue.put(None)
                    
            thread = threading.Thread(target=run_translation_thread, daemon=True)
            thread.start()
            
            while thread.is_alive() or not log_queue.empty():
                try:
                    msg = log_queue.get(block=False)
                    if msg is None:
                        break
                    yield f"data: {json.dumps({'step': 'transcribe', 'status': 'processing', 'message': msg})}\n\n"
                except queue.Empty:
                    yield ": ping\n\n"
                    await asyncio.sleep(0.5)
                    
            if not result_container["success"]:
                err_msg = result_container["error"] or "Lỗi dịch thuật chưa xác định."
                yield f"data: {json.dumps({'step': 'error', 'message': f'Lỗi dịch thuật: {err_msg}'})}\n\n"
                return
                
            subtitles = result_container["subtitles"]
            if not subtitles:
                yield f"data: {json.dumps({'step': 'error', 'message': 'Gemini không trả về bất kỳ kết quả phụ đề nào.'})}\n\n"
                return
                
            yield f"data: {json.dumps({'step': 'transcribe', 'status': 'done', 'message': f'Đã dịch thành công {len(subtitles)} dòng phụ đề!', 'subtitles': subtitles})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'step': 'error', 'message': f'Lỗi hệ thống: {e}'})}\n\n"
            
    return StreamingResponse(log_generator(), media_type="text/event-stream")

@app.post("/api/dub/progress")
async def dub_progress(req: DubbingRequest):
    """SSE endpoint to perform speech generation (TTS) and video merging with live logs"""
    async def log_generator():
        video_path = req.video_path
        if not video_path or not os.path.exists(video_path):
            yield f"data: {json.dumps({'step': 'error', 'message': 'Không tìm thấy file video.'})}\n\n"
            return
            
        subtitles = req.subtitles
        if not subtitles:
            yield f"data: {json.dumps({'step': 'error', 'message': 'Danh sách phụ đề trống.'})}\n\n"
            return
            
        config = migrate_config_secrets_to_keychain(load_config())
        
        video_filename = os.path.basename(video_path)
        base_name = os.path.splitext(video_filename)[0]
        
        # Temp folder for subtitle audio chunks
        chunks_dir = os.path.join(TEMP_DIR, f"chunks_{uuid.uuid4().hex}")
        os.makedirs(chunks_dir, exist_ok=True)
        
        dubbed_audio_path = os.path.join(TEMP_DIR, f"{base_name}_dubbed.mp3")
        srt_path = os.path.join(TEMP_DIR, f"{base_name}_subtitles.srt")
        output_video_filename = f"{base_name}_translated.mp4"
        
        output_dir = config.get("output_dir", "").strip()
        if output_dir and os.path.isdir(output_dir):
            output_video_path = os.path.join(output_dir, output_video_filename)
        else:
            output_video_path = os.path.join(TEMP_DIR, output_video_filename)
        
        try:
            # 1. Voice Synthesis (TTS)
            yield f"data: {json.dumps({'step': 'tts', 'status': 'processing', 'message': f'Bắt đầu lồng tiếng cho {len(subtitles)} đoạn phụ đề sử dụng động cơ {req.tts_engine.upper()}...'})}\n\n"
            
            sub_dicts = []
            voice_config = {}
            if req.tts_engine == "google_cloud":
                voice_config = {
                    "credentials_json": get_secret("google_cloud_credentials"),
                    "voice_name": req.voice_name
                }
                
            total_duration_sec = utils.get_media_duration(video_path)
            total_duration_ms = int(total_duration_sec * 1000)
            
            for i, sub in enumerate(subtitles):
                chunk_filename = f"segment_{sub.index}.mp3"
                chunk_path = os.path.join(chunks_dir, chunk_filename)
                
                target_duration = sub.end_ms - sub.start_ms
                
                msg = f"Đang lồng tiếng dòng {sub.index}/{len(subtitles)}: '{sub.translated_text[:20]}...'"
                yield f"data: {json.dumps({'step': 'tts', 'status': 'processing', 'message': msg})}\n\n"
                
                def generate_single_tts(text=sub.translated_text, start=sub.start_ms, end=sub.end_ms):
                    def inner_callback(msg):
                        print(f"[TTS DEBUG] {msg}")
                    return utils.generate_tts_audio(
                        text=text,
                        lang=config.get("target_lang", "vi"),
                        engine=req.tts_engine,
                        output_path=chunk_path,
                        voice_config=voice_config,
                        target_duration_ms=target_duration,
                        base_speed=req.base_speed,
                        match_duration=req.match_duration,
                        log_callback=inner_callback
                    )
                    
                success = await asyncio.to_thread(generate_single_tts)
                if not success:
                    yield f"data: {json.dumps({'step': 'error', 'message': f'Lỗi không thể tạo giọng đọc cho dòng số {sub.index}.'})}\n\n"
                    # Clean up
                    shutil.rmtree(chunks_dir, ignore_errors=True)
                    return
                    
                sub_dicts.append({
                    "index": sub.index,
                    "start_ms": sub.start_ms,
                    "end_ms": sub.end_ms,
                    "translated_text": sub.translated_text,
                    "audio_path": chunk_path
                })
                
            # 2. Assemble audio chunks into single dubbed track
            yield f"data: {json.dumps({'step': 'tts', 'status': 'processing', 'message': 'Đang đồng bộ hóa và ghép các file giọng đọc thành track hoàn chỉnh...'})}\n\n"
            
            def run_assembly():
                from pydub import AudioSegment
                AudioSegment.converter = utils.get_ffmpeg_path("ffmpeg")
                AudioSegment.ffprobe = utils.get_ffmpeg_path("ffprobe")
                
                # Create silent base track matching video duration
                base_track = AudioSegment.silent(duration=total_duration_ms)
                for item in sub_dicts:
                    if os.path.exists(item["audio_path"]):
                        clip = AudioSegment.from_file(item["audio_path"])
                        base_track = base_track.overlay(clip, position=item["start_ms"])
                base_track.export(dubbed_audio_path, format="mp3")
                
            await asyncio.to_thread(run_assembly)
            
            yield f"data: {json.dumps({'step': 'tts', 'status': 'done', 'message': 'Lồng tiếng và đồng bộ hóa âm thanh thành công!'})}\n\n"
            await asyncio.sleep(0.5)
            
            # 3. Create SRT subtitle file
            utils.make_subtitles_srt(sub_dicts, srt_path)
            
            # 4. Merge Audio and Video
            yield f"data: {json.dumps({'step': 'merge', 'status': 'processing', 'message': 'Đang mix âm thanh lồng tiếng với video gốc...'})}\n\n"
            
            import queue
            import threading
            
            merge_queue = queue.Queue()
            merge_container = {"success": False, "error": None}
            
            def run_merge_thread():
                def callback(msg):
                    merge_queue.put(msg)
                try:
                    res = utils.merge_dubbed_audio_to_video(
                        video_path=video_path,
                        dubbed_audio_path=dubbed_audio_path,
                        output_path=output_video_path,
                        original_vol=req.original_vol,
                        dub_vol=req.dub_vol,
                        srt_path=srt_path,
                        burn_subtitles=req.burn_subtitles,
                        log_callback=callback
                    )
                    merge_container["success"] = res
                except Exception as ex:
                    merge_container["error"] = str(ex)
                    merge_container["success"] = False
                finally:
                    merge_queue.put(None)
                    
            m_thread = threading.Thread(target=run_merge_thread, daemon=True)
            m_thread.start()
            
            while m_thread.is_alive() or not merge_queue.empty():
                try:
                    msg = merge_queue.get(block=False)
                    if msg is None:
                        break
                    yield f"data: {json.dumps({'step': 'merge', 'status': 'processing', 'message': msg})}\n\n"
                except queue.Empty:
                    yield ": ping\n\n"
                    await asyncio.sleep(0.5)
                    
            if not merge_container["success"]:
                err_msg = merge_container["error"] or "Lỗi mix video chưa xác định."
                yield f"data: {json.dumps({'step': 'error', 'message': f'Thất bại khi ghép âm thanh lồng tiếng vào video: {err_msg}'})}\n\n"
                return
                
            # Clean up chunks
            shutil.rmtree(chunks_dir, ignore_errors=True)
            
            # Copy to temp for browser preview if using a custom output dir
            if output_dir and os.path.isdir(output_dir):
                try:
                    shutil.copy2(output_video_path, os.path.join(TEMP_DIR, output_video_filename))
                except Exception as e:
                    print(f"Error copying preview to temp: {e}")
            
            # Send relative preview URL (since /temp is mounted)
            preview_url = f"/temp/{output_video_filename}"
            yield f"data: {json.dumps({'step': 'merge', 'status': 'done', 'message': 'Hoàn thành lồng tiếng & ghép phụ đề xuất sắc!', 'preview_url': preview_url, 'absolute_path': output_video_path})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'step': 'error', 'message': f'Lỗi hệ thống: {e}'})}\n\n"
            shutil.rmtree(chunks_dir, ignore_errors=True)
            
    return StreamingResponse(log_generator(), media_type="text/event-stream")
