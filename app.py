import os
import json
import asyncio
import uuid
import shutil
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List, Optional

import utils

app = FastAPI(title="Video Translate Pro")

# Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Mount static files and templates
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/temp", StaticFiles(directory=TEMP_DIR), name="temp") # Allow streaming/downloading preview videos easily
templates = Jinja2Templates(directory=TEMPLATES_DIR)

CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

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
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False

# Pydantic schemas for request payloads
class ConfigUpdate(BaseModel):
    gemini_key: str
    google_cloud_credentials: Optional[str] = ""
    src_lang: Optional[str] = "auto"
    target_lang: Optional[str] = "vi"

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
    config = load_config()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"config": config}
    )

# API routes
@app.get("/api/config")
async def get_config():
    return JSONResponse(content=load_config())

@app.post("/api/config")
async def update_config(data: ConfigUpdate):
    config = load_config()
    config.update(data.model_dump())
    if save_config(config):
        return {"status": "success", "message": "Lưu cài đặt thành công!"}
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
async def translate_progress(video_path: str, src_lang: str, target_lang: str, gemini_key: Optional[str] = None):
    """SSE endpoint to perform transcription & translation with live progress logs"""
    async def log_generator():
        # Validate inputs
        if not video_path or not os.path.exists(video_path):
            yield f"data: {json.dumps({'step': 'error', 'message': 'Không tìm thấy file video nguồn.'})}\n\n"
            return
            
        nonlocal gemini_key
        if not gemini_key:
            config = load_config()
            gemini_key = config.get("gemini_key")
            
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
            
            def run_extraction():
                return utils.extract_audio_from_video(video_path, audio_path)
                
            success = await asyncio.to_thread(run_extraction)
            if not success:
                yield f"data: {json.dumps({'step': 'error', 'message': 'Không thể trích xuất âm thanh từ video.'})}\n\n"
                return
                
            yield f"data: {json.dumps({'step': 'extract', 'status': 'done', 'message': 'Trích xuất âm thanh thành công!'})}\n\n"
            await asyncio.sleep(0.5)
            
            # 3. Transcribe & Translate
            yield f"data: {json.dumps({'step': 'transcribe', 'status': 'processing', 'message': 'Đang gửi âm thanh lên Google Gemini 2.0 Flash để nhận diện & dịch thuật...'})}\n\n"
            
            def run_translation():
                logs = []
                def callback(msg):
                    logs.append(msg)
                
                res = utils.transcribe_and_translate_audio(
                    audio_path=audio_path,
                    gemini_key=gemini_key,
                    src_lang=src_lang,
                    target_lang=target_lang,
                    log_callback=callback
                )
                return res, logs
                
            subtitles, translation_logs = await asyncio.to_thread(run_translation)
            
            # Emit intermediate progress logs from translation
            for log in translation_logs:
                yield f"data: {json.dumps({'step': 'transcribe', 'status': 'processing', 'message': log})}\n\n"
                await asyncio.sleep(0.1)
                
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
            
        config = load_config()
        
        video_filename = os.path.basename(video_path)
        base_name = os.path.splitext(video_filename)[0]
        
        # Temp folder for subtitle audio chunks
        chunks_dir = os.path.join(TEMP_DIR, f"chunks_{uuid.uuid4().hex}")
        os.makedirs(chunks_dir, exist_ok=True)
        
        dubbed_audio_path = os.path.join(TEMP_DIR, f"{base_name}_dubbed.mp3")
        srt_path = os.path.join(TEMP_DIR, f"{base_name}_subtitles.srt")
        output_video_filename = f"{base_name}_translated.mp4"
        output_video_path = os.path.join(TEMP_DIR, output_video_filename)
        
        try:
            # 1. Voice Synthesis (TTS)
            yield f"data: {json.dumps({'step': 'tts', 'status': 'processing', 'message': f'Bắt đầu lồng tiếng cho {len(subtitles)} đoạn phụ đề sử dụng động cơ {req.tts_engine.upper()}...'})}\n\n"
            
            sub_dicts = []
            voice_config = {}
            if req.tts_engine == "google_cloud":
                voice_config = {
                    "credentials_json": config.get("google_cloud_credentials"),
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
            
            def run_merge():
                logs = []
                def callback(msg):
                    logs.append(msg)
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
                return res, logs
                
            merge_success, merge_logs = await asyncio.to_thread(run_merge)
            
            for log in merge_logs:
                yield f"data: {json.dumps({'step': 'merge', 'status': 'processing', 'message': log})}\n\n"
                await asyncio.sleep(0.1)
                
            if not merge_success:
                yield f"data: {json.dumps({'step': 'error', 'message': 'Thất bại khi ghép âm thanh lồng tiếng vào video.'})}\n\n"
                return
                
            # Clean up chunks
            shutil.rmtree(chunks_dir, ignore_errors=True)
            
            # Send relative preview URL (since /temp is mounted)
            preview_url = f"/temp/{output_video_filename}"
            yield f"data: {json.dumps({'step': 'merge', 'status': 'done', 'message': 'Hoàn thành lồng tiếng & ghép phụ đề xuất sắc!', 'preview_url': preview_url, 'absolute_path': output_video_path})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'step': 'error', 'message': f'Lỗi hệ thống: {e}'})}\n\n"
            shutil.rmtree(chunks_dir, ignore_errors=True)
            
    return StreamingResponse(log_generator(), media_type="text/event-stream")
