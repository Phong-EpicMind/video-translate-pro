"""Local web UI: FastAPI backend + the existing single-page frontend.

Bound to localhost only. Keeps the same SSE/JSON contract the frontend
(``static/js/main.js``) expects, so the UI works unchanged from the old app.
"""

from __future__ import annotations

import asyncio
import json
import os
import queue
import shutil
import socket
import subprocess
import sys
import threading
import uuid
import webbrowser
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from .. import config
from ..core import (
    Subtitle,
    export_subtitled_video,
    extract_audio,
    get_duration,
    mux_dubbed_audio,
    synthesize_segments,
    write_srt,
)
from ..core.assemble import assemble_dub_track
from ..filenames import sanitize_stem, unique_path
from ..pipeline import transcribe_translate

LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}

# Only one native folder dialog may be open at a time: a dialog opened by a
# background process does not steal focus, so users used to click again and
# get a second dialog queued behind the first.
_folder_dialog_lock = threading.Lock()
WEB_DIR = Path(__file__).resolve().parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"


def create_app(local_only: bool = True) -> FastAPI:
    config.ensure_dirs()
    temp_dir = config.temp_dir()

    app = FastAPI(title="TranslateDub AI")
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.mount("/temp", StaticFiles(directory=str(temp_dir)), name="temp")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    if local_only:
        @app.middleware("http")
        async def local_only_guard(request: Request, call_next):
            host = request.client.host if request.client else ""
            if host not in LOCAL_HOSTS:
                return JSONResponse(status_code=403, content={"detail": "Local access only."})
            return await call_next(request)

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        return templates.TemplateResponse(
            request=request, name="index.html",
            context={"config": config.public_config()},
        )

    @app.get("/api/config")
    async def get_config():
        return JSONResponse(content=config.public_config())

    @app.post("/api/config")
    async def update_config(data: ConfigUpdate):
        incoming = data.model_dump(exclude_unset=True)
        pub = config.update_settings(incoming)
        if not pub["has_gemini_key"]:
            asr_free = any(e["available"] for e in pub["asr_engines"] if e["name"] != "gemini")
            tr_free = any(e["available"] for e in pub["translate_engines"] if e["name"] != "gemini")
            if not (asr_free and tr_free):
                raise HTTPException(
                    status_code=400,
                    detail="Cần một Gemini API Key, hoặc cài engine miễn phí: "
                           "pip install \"translatedub[free]\".",
                )
        return {"status": "success", "message": "Lưu cài đặt thành công!", "config": pub}

    @app.post("/api/upload")
    async def upload_video(file: UploadFile = File(...)):
        try:
            ext = (os.path.splitext(file.filename or "")[1] or ".mp4").lower()
            stem = sanitize_stem(file.filename or "video")
            name = f"{stem}_{uuid.uuid4().hex[:10]}{ext}"
            path = temp_dir / name
            with open(path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            return {"status": "success", "video_path": str(path), "filename": file.filename}
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"Lỗi tải video: {exc}")

    @app.post("/api/reveal")
    async def reveal(payload: RevealRequest):
        path = payload.path
        if not path or not os.path.exists(path):
            return {"ok": False, "error": "File không tồn tại."}
        try:
            _reveal_in_file_manager(path)
            return {"ok": True}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    @app.post("/api/pick-folder")
    async def pick_folder():
        if not _folder_dialog_lock.acquire(blocking=False):
            return {"ok": False, "path": "", "busy": True}
        try:
            path = await asyncio.to_thread(_pick_folder_native)
        finally:
            _folder_dialog_lock.release()
        return {"ok": bool(path), "path": path or ""}

    @app.get("/api/translate/progress")
    async def translate_progress(video_path: str, src_lang: str, target_lang: str):
        return StreamingResponse(
            _translate_stream(video_path, src_lang, target_lang, temp_dir),
            media_type="text/event-stream",
        )

    @app.post("/api/dub/progress")
    async def dub_progress(req: DubbingRequest):
        return StreamingResponse(_dub_stream(req, temp_dir), media_type="text/event-stream")

    return app


# ----- request models -------------------------------------------------------

class ConfigUpdate(BaseModel):
    gemini_key: Optional[str] = None
    google_cloud_credentials: Optional[str] = None
    src_lang: Optional[str] = None
    target_lang: Optional[str] = None
    asr_engine: Optional[str] = None
    translate_engine: Optional[str] = None
    whisper_model: Optional[str] = None
    tts_engine: Optional[str] = None
    voice_name: Optional[str] = None
    base_speed: Optional[float] = None
    match_duration: Optional[bool] = None
    output_dir: Optional[str] = None


class RevealRequest(BaseModel):
    path: str


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
    tts_engine: str
    voice_name: Optional[str] = ""
    base_speed: Optional[float] = 1.0
    match_duration: Optional[bool] = True
    output_mode: Optional[str] = "dubbed"
    source_filename: Optional[str] = ""


# ----- helpers --------------------------------------------------------------

def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _reveal_in_file_manager(path: str) -> None:
    if sys.platform == "darwin":
        subprocess.run(["open", "-R", path], check=False)
    elif os.name == "nt":
        subprocess.run(["explorer", "/select,", os.path.normpath(path)], check=False)
    else:
        subprocess.run(["xdg-open", os.path.dirname(path)], check=False)


def _pick_folder_native() -> "Optional[str]":
    """Open the OS-native "choose folder" dialog on this machine and return the path.

    Returns None when cancelled or no dialog tool is available. Local-first only:
    the dialog appears on the same machine that runs the server.
    """
    try:
        if sys.platform == "darwin":
            choose = 'POSIX path of (choose folder with prompt "Chọn thư mục lưu video")'
            # Host the dialog in Finder: a dialog opened by a background process
            # does not come to the front on its own ('tell me to activate' is not
            # enough — verified with System Events), which reads as "nothing
            # happened" and invites a second click. Finder CAN activate.
            finder_script = f'tell application "Finder"\nactivate\n{choose}\nend tell'
            result = subprocess.run(["osascript", "-e", finder_script],
                                    capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip() or None
            if "-128" in (result.stderr or ""):
                return None  # user cancelled — do not open another dialog
            # Automation permission denied (or Finder unavailable): fall back to
            # a plain dialog. It may open behind other windows but still works.
            result = subprocess.run(["osascript", "-e", choose],
                                    capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip() or None
        elif os.name == "nt":
            ps = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                "$d = New-Object System.Windows.Forms.FolderBrowserDialog; "
                "if ($d.ShowDialog() -eq 'OK') { Write-Output $d.SelectedPath }"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                capture_output=True, text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        else:  # Linux / BSD: try common dialog tools
            for cmd in (
                ["zenity", "--file-selection", "--directory",
                 "--title=Chọn thư mục lưu video"],
                ["kdialog", "--getexistingdirectory", os.path.expanduser("~")],
            ):
                if shutil.which(cmd[0]):
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode == 0 and result.stdout.strip():
                        return result.stdout.strip()
                    return None
    except Exception:  # noqa: BLE001 - a missing/failed dialog is non-fatal
        return None
    return None


def _voice_config_for(req: "DubbingRequest") -> dict:
    """Voice settings for the chosen engine. The selected voice must reach
    EVERY engine — it used to be wired only for google_cloud, so edge silently
    ignored the user's voice choice (e.g. NamMinh) and used its default."""
    cfg = {"voice_name": req.voice_name or ""}
    if req.tts_engine == "google_cloud":
        cfg["credentials_json"] = config.get_secret("google_cloud_credentials")
    return cfg


def _resolve_output_path(base_filename: str, temp_dir: Path) -> str:
    output_dir = (config.load_config().get("output_dir") or "").strip()
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        if os.path.isdir(output_dir):
            return unique_path(output_dir, base_filename)
    return unique_path(str(temp_dir), base_filename)


def _preview_url(output_path: str, temp_dir: Path) -> str:
    filename = os.path.basename(output_path)
    if os.path.abspath(os.path.dirname(output_path)) == os.path.abspath(str(temp_dir)):
        return f"/temp/{filename}"
    preview_name = f"preview_{uuid.uuid4().hex}_{filename}"
    shutil.copy2(output_path, temp_dir / preview_name)
    return f"/temp/{preview_name}"


async def _drain_thread(work, container: dict, step: str):
    """Run ``work`` in a thread, streaming its queued log messages as SSE events."""
    q: queue.Queue = queue.Queue()

    def runner():
        try:
            container["result"] = work(q.put)
        except Exception as exc:  # noqa: BLE001
            container["error"] = str(exc)
        finally:
            q.put(None)

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    while thread.is_alive() or not q.empty():
        try:
            msg = q.get(block=False)
            if msg is None:
                break
            yield _sse({"step": step, "status": "processing", "message": msg})
        except queue.Empty:
            yield ": ping\n\n"
            await asyncio.sleep(0.3)


async def _translate_stream(video_path: str, src_lang: str, target_lang: str, temp_dir: Path):
    if not video_path or not os.path.exists(video_path):
        yield _sse({"step": "error", "message": "Không tìm thấy file video nguồn."})
        return
    gemini_key = config.get_secret("gemini_key")
    settings = config.load_config()
    asr_engine = settings.get("asr_engine", "auto")
    translate_engine = settings.get("translate_engine", "auto")
    whisper_model = settings.get("whisper_model", "small")

    stem = os.path.splitext(os.path.basename(video_path))[0]
    audio_path = str(temp_dir / f"{stem}_{uuid.uuid4().hex[:8]}.mp3")

    yield _sse({"step": "extract", "status": "processing", "message": "Trích xuất âm thanh..."})
    extract_box: dict = {}
    async for event in _drain_thread(
        lambda put: extract_audio(video_path, audio_path, put), extract_box, "extract"
    ):
        yield event
    if extract_box.get("error") or not extract_box.get("result"):
        yield _sse({"step": "error", "message": "Không thể trích xuất âm thanh."})
        return
    yield _sse({"step": "extract", "status": "done", "message": "Trích xuất âm thanh xong!"})

    yield _sse({"step": "transcribe", "status": "processing",
                "message": "Đang nhận diện giọng nói & dịch..."})
    box: dict = {}
    async for event in _drain_thread(
        lambda put: transcribe_translate(
            audio_path, src_lang, target_lang, gemini_key=gemini_key,
            asr_engine=asr_engine, translate_engine=translate_engine,
            whisper_model=whisper_model, log=put,
        ),
        box, "transcribe",
    ):
        yield event
    try:
        os.remove(audio_path)
    except OSError:
        pass
    if box.get("error"):
        yield _sse({"step": "error", "message": f"Lỗi dịch thuật: {box['error']}"})
        return
    subtitles: list[Subtitle] = box.get("result") or []
    if not subtitles:
        yield _sse({"step": "error", "message": "Gemini không trả về phụ đề nào."})
        return
    yield _sse({
        "step": "transcribe", "status": "done",
        "message": f"Đã dịch {len(subtitles)} dòng phụ đề!",
        "subtitles": [s.to_dict() for s in subtitles],
    })


async def _dub_stream(req: DubbingRequest, temp_dir: Path):
    video_path = req.video_path
    if not video_path or not os.path.exists(video_path):
        yield _sse({"step": "error", "message": "Không tìm thấy file video."})
        return
    if not req.subtitles:
        yield _sse({"step": "error", "message": "Danh sách phụ đề trống."})
        return

    mode = req.output_mode if req.output_mode in {"dubbed", "subtitles_only"} else "dubbed"
    base = sanitize_stem(req.source_filename or video_path)
    suffix = "subtitled" if mode == "subtitles_only" else "translated"
    subtitles = [
        Subtitle(s.index, s.start_ms, s.end_ms, s.original_text, s.translated_text)
        for s in req.subtitles
    ]

    srt_path = str(temp_dir / f"{base}_{uuid.uuid4().hex[:8]}.srt")
    write_srt(subtitles, srt_path)
    output_path = _resolve_output_path(f"{base}_{suffix}.mp4", temp_dir)

    if mode == "subtitles_only":
        yield _sse({"step": "subtitle", "status": "processing",
                    "message": f"Đang xuất video phụ đề ({len(subtitles)} dòng)..."})
        box: dict = {}
        async for event in _drain_thread(
            lambda put: export_subtitled_video(video_path, srt_path, output_path,
                                               req.burn_subtitles, put),
            box, "merge",
        ):
            yield event
        if box.get("error") or not box.get("result"):
            yield _sse({"step": "error", "message": "Thất bại khi xuất video phụ đề."})
            return
        yield _sse({"step": "merge", "status": "done", "message": "Hoàn thành xuất video phụ đề!",
                    "preview_url": _preview_url(output_path, temp_dir),
                    "absolute_path": output_path, "output_mode": mode})
        return

    voice_config = _voice_config_for(req)
    if req.tts_engine == "google_cloud" and not voice_config.get("credentials_json"):
        yield _sse({"step": "error", "message": "Chưa có Google Cloud credentials."})
        return

    chunks_dir = temp_dir / f"chunks_{uuid.uuid4().hex}"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    dubbed_audio = str(temp_dir / f"{base}_{uuid.uuid4().hex[:8]}_dub.mp3")
    target_lang = config.load_config().get("target_lang", "vi")

    try:
        yield _sse({"step": "tts", "status": "processing",
                    "message": f"Tạo thuyết minh cho {len(subtitles)} dòng ({req.tts_engine})..."})
        tts_box: dict = {}

        def _tts_work(put):
            def _progress(i, n, sub):
                put(f"Dòng {i}/{n}: '{sub.translated_text[:20]}...'")

            return synthesize_segments(
                subtitles, lang=target_lang, engine=req.tts_engine,
                chunks_dir=str(chunks_dir), voice_config=voice_config,
                base_speed=req.base_speed or 1.0,
                match_duration=req.match_duration if req.match_duration is not None else True,
                log=put, progress=_progress,
            )

        async for event in _drain_thread(_tts_work, tts_box, "tts"):
            yield event
        if tts_box.get("error") or not tts_box.get("result"):
            yield _sse({"step": "error",
                        "message": f"Lỗi tạo giọng đọc: {tts_box.get('error', 'không rõ')}"})
            return

        yield _sse({"step": "tts", "status": "processing", "message": "Đồng bộ & ghép track..."})
        total_ms = int(get_duration(video_path) * 1000)
        await asyncio.to_thread(assemble_dub_track, subtitles, total_ms, dubbed_audio)
        yield _sse({"step": "tts", "status": "done", "message": "Thuyết minh xong!"})

        yield _sse({"step": "merge", "status": "processing", "message": "Đang mix với video..."})
        box = {}
        async for event in _drain_thread(
            lambda put: mux_dubbed_audio(video_path, dubbed_audio, output_path,
                                         req.original_vol, req.dub_vol, srt_path=srt_path,
                                         burn_subtitles=req.burn_subtitles, log=put),
            box, "merge",
        ):
            yield event
        if box.get("error") or not box.get("result"):
            yield _sse({"step": "error", "message": "Thất bại khi ghép video."})
            return
        yield _sse({"step": "merge", "status": "done", "message": "Hoàn thành thuyết minh!",
                    "preview_url": _preview_url(output_path, temp_dir),
                    "absolute_path": output_path, "output_mode": mode})
    finally:
        shutil.rmtree(chunks_dir, ignore_errors=True)


# ----- serve entrypoint -----------------------------------------------------

def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def serve(host: str = "127.0.0.1", port: int = 0, open_browser: bool = True) -> None:
    import uvicorn

    if not port:
        port = _free_port()
    url = f"http://{host}:{port}"
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    print(f"TranslateDub AI running at {url}  (Ctrl+C to stop)")
    uvicorn.run(create_app(), host=host, port=port, log_level="warning")
