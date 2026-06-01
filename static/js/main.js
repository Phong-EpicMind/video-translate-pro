// State Variables
let currentVideoPath = "";
let currentSubtitles = [];

// Google Cloud TTS Premium Voices Database
const PREMIUM_VOICES = {
    "vi": [
        { value: "vi-VN-Neural2-A", label: "Giọng Nữ - Miền Bắc (Neural2-A)" },
        { value: "vi-VN-Neural2-D", label: "Giọng Nam - Miền Bắc (Neural2-D)" },
        { value: "vi-VN-Neural2-C", label: "Giọng Nữ - Miền Nam (Neural2-C)" },
        { value: "vi-VN-Neural2-B", label: "Giọng Nam - Miền Nam (Neural2-B)" },
        { value: "vi-VN-Wavenet-A", label: "Giọng Nữ - Miền Bắc (Wavenet-A)" },
        { value: "vi-VN-Wavenet-B", label: "Giọng Nam - Miền Bắc (Wavenet-B)" },
        { value: "vi-VN-Wavenet-C", label: "Giọng Nữ - Miền Nam (Wavenet-C)" },
        { value: "vi-VN-Wavenet-D", label: "Giọng Nam - Miền Nam (Wavenet-D)" },
        { value: "vi-VN-Standard-A", label: "Giọng Nữ - Miền Bắc (Standard-A)" },
        { value: "vi-VN-Standard-B", label: "Giọng Nam - Miền Bắc (Standard-B)" },
        { value: "vi-VN-Standard-C", label: "Giọng Nữ - Miền Nam (Standard-C)" },
        { value: "vi-VN-Standard-D", label: "Giọng Nam - Miền Nam (Standard-D)" }
    ],
    "en": [
        { value: "en-US-Neural2-F", label: "Giọng Nữ - US (Neural2-F)" },
        { value: "en-US-Neural2-O", label: "Giọng Nam - US (Neural2-O)" },
        { value: "en-US-News-K", label: "Giọng Nữ - US News (News-K)" },
        { value: "en-GB-Neural2-F", label: "Giọng Nữ - UK (Neural2-F)" },
        { value: "en-GB-Neural2-B", label: "Giọng Nam - UK (Neural2-B)" },
        { value: "en-US-Wavenet-F", label: "Giọng Nữ - US (Wavenet-F)" },
        { value: "en-US-Wavenet-D", label: "Giọng Nam - US (Wavenet-D)" }
    ],
    "zh": [
        { value: "cmn-CN-Neural2-A", label: "Giọng Nữ - Mandarin (Neural2-A)" },
        { value: "cmn-CN-Neural2-B", label: "Giọng Nam - Mandarin (Neural2-B)" },
        { value: "cmn-CN-Wavenet-A", label: "Giọng Nữ - Mandarin (Wavenet-A)" },
        { value: "cmn-CN-Wavenet-B", label: "Giọng Nam - Mandarin (Wavenet-B)" }
    ],
    "ja": [
        { value: "ja-JP-Neural2-B", label: "Giọng Nữ - Tiêu chuẩn (Neural2-B)" },
        { value: "ja-JP-Neural2-C", label: "Giọng Nam - Tiêu chuẩn (Neural2-C)" },
        { value: "ja-JP-Wavenet-A", label: "Giọng Nữ - Tiêu chuẩn (Wavenet-A)" },
        { value: "ja-JP-Wavenet-D", label: "Giọng Nam - Tiêu chuẩn (Wavenet-D)" }
    ],
    "ko": [
        { value: "ko-KR-Neural2-A", label: "Giọng Nữ - Tiêu chuẩn (Neural2-A)" },
        { value: "ko-KR-Neural2-C", label: "Giọng Nam - Tiêu chuẩn (Neural2-C)" },
        { value: "ko-KR-Wavenet-A", label: "Giọng Nữ - Tiêu chuẩn (Wavenet-A)" },
        { value: "ko-KR-Wavenet-C", label: "Giọng Nam - Tiêu chuẩn (Wavenet-C)" }
    ],
    "fr": [
        { value: "fr-FR-Neural2-A", label: "Giọng Nữ - Tiêu chuẩn (Neural2-A)" },
        { value: "fr-FR-Neural2-B", label: "Giọng Nam - Tiêu chuẩn (Neural2-B)" }
    ],
    "de": [
        { value: "de-DE-Neural2-F", label: "Giọng Nữ - Tiêu chuẩn (Neural2-F)" },
        { value: "de-DE-Neural2-I", label: "Giọng Nam - Tiêu chuẩn (Neural2-I)" }
    ],
    "es": [
        { value: "es-ES-Neural2-F", label: "Giọng Nữ - Tiêu chuẩn (Neural2-F)" },
        { value: "es-ES-Neural2-B", label: "Giọng Nam - Tiêu chuẩn (Neural2-B)" }
    ]
};

function updateVoiceDropdown(lang) {
    if (!voiceName) return;
    voiceName.innerHTML = "";
    const voices = PREMIUM_VOICES[lang] || PREMIUM_VOICES["vi"];
    voices.forEach(v => {
        const opt = document.createElement("option");
        opt.value = v.value;
        opt.textContent = v.label;
        voiceName.appendChild(opt);
    });
}

// DOM Elements
const dropzoneState = document.getElementById("dropzoneState");
const processingState = document.getElementById("processingState");
const subtitleEditorState = document.getElementById("subtitleEditorState");
const completeState = document.getElementById("completeState");

const uploadBox = document.getElementById("uploadBox");
const videoFileInput = document.getElementById("videoFileInput");
const localVideoPath = document.getElementById("localVideoPath");
const localPathSubmitBtn = document.getElementById("localPathSubmitBtn");

const consoleBody = document.getElementById("consoleBody");
const processingProgressBar = document.getElementById("processingProgressBar");
const pipelineTitle = document.getElementById("pipelineTitle");

const editorVideoPlayer = document.getElementById("editorVideoPlayer");
const editorVideoFilename = document.getElementById("editorVideoFilename");
const subtitleTableBody = document.getElementById("subtitleTableBody");
const cancelDubBtn = document.getElementById("cancelDubBtn");
const startDubBtn = document.getElementById("startDubBtn");

const finalVideoPlayer = document.getElementById("finalVideoPlayer");
const finalVideoPath = document.getElementById("finalVideoPath");
const downloadVideoBtn = document.getElementById("downloadVideoBtn");
const startOverBtn = document.getElementById("startOverBtn");
const headerStartOverBtn = document.getElementById("headerStartOverBtn");

// Sidebar configuration elements
const geminiKey = document.getElementById("geminiKey");
const toggleGeminiKey = document.getElementById("toggleGeminiKey");
const outputDir = document.getElementById("outputDir");
const selectOutputDirBtn = document.getElementById("selectOutputDirBtn");
const ttsEngine = document.getElementById("ttsEngine");
const gcpCredentials = document.getElementById("gcpCredentials");
const toggleGcpCredentials = document.getElementById("toggleGcpCredentials");
const gcpCredentialsGroup = document.getElementById("gcpCredentialsGroup");
const srcLang = document.getElementById("srcLang");
const targetLang = document.getElementById("targetLang");
const voiceName = document.getElementById("voiceName");
const voiceNameGroup = document.getElementById("voiceNameGroup");
const baseSpeed = document.getElementById("baseSpeed");
const baseSpeedVal = document.getElementById("baseSpeedVal");
const matchDuration = document.getElementById("matchDuration");
const originalVol = document.getElementById("originalVol");
const originalVolVal = document.getElementById("originalVolVal");
const dubVol = document.getElementById("dubVol");
const dubVolVal = document.getElementById("dubVolVal");
const burnSubtitles = document.getElementById("burnSubtitles");
const saveConfigBtn = document.getElementById("saveConfigBtn");

// Initialize Application
document.addEventListener("DOMContentLoaded", () => {
    loadConfig();
    setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
    // Gemini key toggle visibility
    toggleGeminiKey.addEventListener("click", () => {
        if (geminiKey.type === "password") {
            geminiKey.type = "text";
            toggleGeminiKey.innerHTML = '<i class="fa-solid fa-eye-slash"></i>';
        } else {
            geminiKey.type = "password";
            toggleGeminiKey.innerHTML = '<i class="fa-solid fa-eye"></i>';
        }
    });

    // GCP credentials toggle visibility
    if (toggleGcpCredentials) {
        toggleGcpCredentials.addEventListener("click", () => {
            if (gcpCredentials.style.webkitTextSecurity === "none") {
                gcpCredentials.style.webkitTextSecurity = "disc";
                toggleGcpCredentials.innerHTML = '<i class="fa-solid fa-eye"></i>';
            } else {
                gcpCredentials.style.webkitTextSecurity = "none";
                toggleGcpCredentials.innerHTML = '<i class="fa-solid fa-eye-slash"></i>';
            }
        });
    }

    // Select output directory click
    if (selectOutputDirBtn) {
        selectOutputDirBtn.addEventListener("click", async () => {
            if (window.pywebview && window.pywebview.api && window.pywebview.api.select_directory) {
                try {
                    const selected = await window.pywebview.api.select_directory();
                    if (selected) {
                        outputDir.value = selected;
                        showToast("Đã chọn thư mục lưu: " + selected.split("/").pop());
                    }
                } catch (err) {
                    console.error("Lỗi gọi API chọn thư mục:", err);
                }
            } else {
                showToast("Vui lòng nhập/dán đường dẫn trực tiếp vào ô cấu hình.");
            }
        });
    }

    // Handle Engine Toggle to show/hide credentials
    ttsEngine.addEventListener("change", () => {
        toggleTtsEngineGroups();
    });

    // Target Language change to update voices
    targetLang.addEventListener("change", () => {
        updateVoiceDropdown(targetLang.value);
    });

    // Speed slider
    baseSpeed.addEventListener("input", (e) => {
        baseSpeedVal.textContent = `${parseFloat(e.target.value).toFixed(2)}x`;
    });

    // Volume sliders
    originalVol.addEventListener("input", (e) => {
        originalVolVal.textContent = `${Math.round(e.target.value * 100)}%`;
    });
    dubVol.addEventListener("input", (e) => {
        dubVolVal.textContent = `${Math.round(e.target.value * 100)}%`;
    });

    // Save config
    saveConfigBtn.addEventListener("click", saveConfig);

    // Dropzone drag-and-drop
    uploadBox.addEventListener("dragover", (e) => {
        e.preventDefault();
        uploadBox.classList.add("dragover");
    });
    uploadBox.addEventListener("dragleave", () => {
        uploadBox.classList.remove("dragover");
    });
    uploadBox.addEventListener("drop", (e) => {
        e.preventDefault();
        uploadBox.classList.remove("dragover");
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileUpload(files[0]);
        }
    });

    // File Input change
    videoFileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });

    // Local path submission
    localPathSubmitBtn.addEventListener("click", () => {
        const path = localVideoPath.value.trim();
        if (!path) {
            showToast("Vui lòng nhập đường dẫn video.");
            return;
        }
        saveConfigSilently();
        currentVideoPath = path;
        startTranslationPipeline(path);
    });

    // Navigation buttons
    cancelDubBtn.addEventListener("click", () => {
        switchState(dropzoneState);
        editorVideoPlayer.pause();
        editorVideoPlayer.src = "";
    });

    startDubBtn.addEventListener("click", startDubbingPipeline);

    const resetAppFlow = () => {
        switchState(dropzoneState);
        finalVideoPlayer.pause();
        finalVideoPlayer.src = "";
        editorVideoPlayer.pause();
        editorVideoPlayer.src = "";
        currentVideoPath = "";
        currentSubtitles = [];
        localVideoPath.value = "";
    };

    startOverBtn.addEventListener("click", resetAppFlow);
    if (headerStartOverBtn) {
        headerStartOverBtn.addEventListener("click", resetAppFlow);
    }
}

// Switch between panels
function switchState(activeState) {
    [dropzoneState, processingState, subtitleEditorState, completeState].forEach(state => {
        state.classList.remove("active");
    });
    activeState.classList.add("active");
    
    // Toggle header quick-reset button
    if (headerStartOverBtn) {
        if (activeState === dropzoneState) {
            headerStartOverBtn.style.display = "none";
        } else {
            headerStartOverBtn.style.display = "inline-flex";
            headerStartOverBtn.style.alignItems = "center";
            headerStartOverBtn.style.gap = "6px";
        }
    }
}

// Show temporary notification
function showToast(message) {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.classList.add("show");
    setTimeout(() => {
        toast.classList.remove("show");
    }, 3000);
}

// Load configurations from API
async function loadConfig() {
    try {
        const response = await fetch("/api/config");
        const config = await response.json();
        
        if (config.gemini_key) geminiKey.value = config.gemini_key;
        if (config.output_dir) outputDir.value = config.output_dir;
        if (config.tts_engine) ttsEngine.value = config.tts_engine;
        if (config.google_cloud_credentials) gcpCredentials.value = config.google_cloud_credentials;
        if (config.src_lang) srcLang.value = config.src_lang;
        if (config.target_lang) targetLang.value = config.target_lang;
        
        // Dynamically load voices list
        updateVoiceDropdown(targetLang.value);
        if (config.voice_name) voiceName.value = config.voice_name;
        
        if (config.base_speed) {
            baseSpeed.value = config.base_speed;
            baseSpeedVal.textContent = `${parseFloat(config.base_speed).toFixed(2)}x`;
        }
        if (config.match_duration !== undefined) {
            matchDuration.checked = config.match_duration;
        }
        
        toggleTtsEngineGroups();
    } catch (e) {
        console.error("Lỗi tải cấu hình:", e);
    }
}

// Save configurations to API
async function saveConfig() {
    const data = {
        gemini_key: geminiKey.value.trim(),
        google_cloud_credentials: gcpCredentials.value.trim(),
        tts_engine: ttsEngine.value,
        src_lang: srcLang.value,
        target_lang: targetLang.value,
        voice_name: voiceName.value,
        base_speed: parseFloat(baseSpeed.value),
        match_duration: matchDuration.checked,
        output_dir: outputDir.value.trim()
    };

    if (!data.gemini_key) {
        showToast("Vui lòng nhập Gemini API Key!");
        return;
    }

    try {
        const response = await fetch("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (result.status === "success") {
            showToast("Cài đặt đã được lưu thành công!");
        } else {
            showToast("Có lỗi xảy ra: " + result.detail);
        }
    } catch (e) {
        showToast("Lỗi hệ thống khi lưu cài đặt.");
    }
}

async function saveConfigSilently() {
    const data = {
        gemini_key: geminiKey.value.trim(),
        google_cloud_credentials: gcpCredentials.value.trim(),
        tts_engine: ttsEngine.value,
        src_lang: srcLang.value,
        target_lang: targetLang.value,
        voice_name: voiceName.value,
        base_speed: parseFloat(baseSpeed.value),
        match_duration: matchDuration.checked
    };
    if (!data.gemini_key) return;
    try {
        await fetch("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    } catch (e) {
        console.error("Silent config save error:", e);
    }
}

// Show/hide Google Cloud TTS input groups
function toggleTtsEngineGroups() {
    if (ttsEngine.value === "google_cloud") {
        gcpCredentialsGroup.style.display = "block";
        voiceNameGroup.style.display = "block";
    } else {
        gcpCredentialsGroup.style.display = "none";
        voiceNameGroup.style.display = "none";
    }
}

// Log line to terminal console
function logToConsole(message, type = "system") {
    const line = document.createElement("div");
    line.className = `console-line ${type}`;
    
    // Add timestamp
    const now = new Date();
    const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
    line.innerHTML = `<span class="console-line-time" style="color: var(--text-muted); margin-right: 8px;">[${timeStr}]</span> ${message}`;
    
    consoleBody.appendChild(line);
    consoleBody.scrollTop = consoleBody.scrollHeight;
}

// Upload file to server
async function handleFileUpload(file) {
    // Verify file exists
    if (!file) return;

    if (!geminiKey.value.trim()) {
        showToast("Vui lòng lưu Gemini API Key ở thanh bên trước!");
        return;
    }

    saveConfigSilently();
    switchState(processingState);
    pipelineTitle.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang tải video lên máy chủ...';
    consoleBody.innerHTML = "";
    logToConsole(`Bắt đầu tải file: ${file.name} (${Math.round(file.size / 1024 / 1024)} MB)...`, "info");
    processingProgressBar.style.width = "5%";

    const formData = new FormData();
    formData.append("file", file);

    try {
        const response = await fetch("/api/upload", {
            method: "POST",
            body: formData
        });
        
        if (!response.ok) {
            throw new Error("Không thể tải file lên.");
        }
        
        const data = await response.json();
        if (data.status === "success") {
            logToConsole(`Đã tải video thành công lên: ${data.video_path}`, "success");
            currentVideoPath = data.video_path;
            
            // Start process
            startTranslationPipeline(data.video_path);
        } else {
            logToConsole(`Tải file thất bại: ${data.detail}`, "error");
            showToast("Có lỗi xảy ra khi tải file.");
            switchState(dropzoneState);
        }
    } catch (e) {
        logToConsole(`Lỗi tải video: ${e.message}`, "error");
        showToast("Lỗi kết nối máy chủ.");
        switchState(dropzoneState);
    }
}

// Reset Pipeline UI Flowchart states
function resetPipelineFlowchart() {
    const steps = ["step_init", "step_extract", "step_transcribe", "step_assemble"];
    steps.forEach(id => {
        const el = document.getElementById(id);
        el.className = "flow-step";
    });
    
    // Clear flow lines
    const lines = document.querySelectorAll(".flow-line");
    lines.forEach(line => line.className = "flow-line");
}

// Start Speech-to-Text & Translation (SSE)
function startTranslationPipeline(videoPath) {
    if (!geminiKey.value.trim()) {
        showToast("Vui lòng nhập Gemini API Key ở thanh bên!");
        switchState(dropzoneState);
        return;
    }

    switchState(processingState);
    resetPipelineFlowchart();
    consoleBody.innerHTML = "";
    pipelineTitle.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang trích xuất & Dịch thuật phụ đề...';
    
    document.getElementById("step_init").classList.add("active");
    logToConsole("Khởi tạo tiến trình dịch thuật...", "info");
    logToConsole(`Đường dẫn Video: ${videoPath}`, "system");

    const src = srcLang.value;
    const target = targetLang.value;
    
    const key = geminiKey.value.trim();
    // Initiate Server-Sent Events source
    const sseUrl = `/api/translate/progress?video_path=${encodeURIComponent(videoPath)}&src_lang=${src}&target_lang=${target}&gemini_key=${encodeURIComponent(key)}`;
    const eventSource = new EventSource(sseUrl);

    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        
        if (data.step === "init") {
            document.getElementById("step_init").className = "flow-step success";
            document.getElementById("step_extract").className = "flow-step active";
            logToConsole(data.message, "info");
            processingProgressBar.style.width = "15%";
        } 
        else if (data.step === "extract") {
            if (data.status === "processing") {
                logToConsole(data.message, "system");
                processingProgressBar.style.width = "30%";
            } else if (data.status === "done") {
                document.getElementById("step_extract").className = "flow-step success";
                const flowLines = document.querySelectorAll(".flow-line");
                if (flowLines.length >= 1) flowLines[0].className = "flow-line success";
                document.getElementById("step_transcribe").className = "flow-step active";
                logToConsole(data.message, "success");
                processingProgressBar.style.width = "50%";
            }
        } 
        else if (data.step === "transcribe") {
            if (data.status === "processing") {
                logToConsole(data.message, "system");
                // Slowly increment progress bar for visual engagement
                let currentW = parseFloat(processingProgressBar.style.width);
                if (currentW < 85) {
                    processingProgressBar.style.width = `${currentW + 5}%`;
                }
            } else if (data.status === "done") {
                document.getElementById("step_transcribe").className = "flow-step success";
                const flowLines = document.querySelectorAll(".flow-line");
                if (flowLines.length >= 2) flowLines[1].className = "flow-line success";
                logToConsole(data.message, "success");
                processingProgressBar.style.width = "90%";
                
                currentSubtitles = data.subtitles;
                
                // Finish translation, proceed to Subtitle Editor
                setTimeout(() => {
                    eventSource.close();
                    initSubtitleEditor(data.subtitles);
                }, 1000);
            }
        } 
        else if (data.step === "error") {
            logToConsole(data.message, "error");
            showToast("Lỗi xử lý dịch thuật.");
            
            // Mark current active step as error
            const activeStep = document.querySelector(".flow-step.active");
            if (activeStep) activeStep.classList.add("error");
            
            eventSource.close();
        }
    };

    eventSource.onerror = function() {
        logToConsole("Mất kết nối máy chủ khi đang truyền log.", "error");
        eventSource.close();
    };
}

// Render Subtitle Editor Grid
function initSubtitleEditor(subtitles) {
    switchState(subtitleEditorState);
    subtitleTableBody.innerHTML = "";
    
    // Set video file preview path (if it's a temp upload file, load it locally)
    let relativeVideoUrl = "";
    if (currentVideoPath.includes("/temp/")) {
        relativeVideoUrl = `/temp/${currentVideoPath.split("/temp/")[1]}`;
    } else {
        // Fallback for direct local path: serve via raw file system streaming or default
        relativeVideoUrl = `/temp/${currentVideoPath.split("/").pop()}`;
    }
    
    editorVideoPlayer.src = relativeVideoUrl;
    editorVideoFilename.innerHTML = `<i class="fa-solid fa-video"></i> ${currentVideoPath.split("/").pop()}`;
    
    subtitles.forEach(sub => {
        const tr = document.createElement("tr");
        tr.id = `sub_row_${sub.index}`;
        
        // Milliseconds converted to string for standard presentation
        const startStr = msToTimeStr(sub.start_ms);
        const endStr = msToTimeStr(sub.end_ms);
        
        tr.innerHTML = `
            <td class="subtitle-index">${sub.index}</td>
            <td class="time-range">
                <input type="text" class="sub-start-input" data-index="${sub.index}" value="${startStr}" placeholder="00:00:00.000">
                <input type="text" class="sub-end-input" data-index="${sub.index}" value="${endStr}" placeholder="00:00:00.000">
            </td>
            <td class="sub-text-orig">${escapeHtml(sub.original_text)}</td>
            <td class="sub-text-trans">
                <input type="text" class="sub-trans-input" data-index="${sub.index}" value="${escapeHtml(sub.translated_text)}">
            </td>
            <td>
                <button type="button" class="btn-play-row" onclick="playSubtitleSegment(${sub.start_ms}, ${sub.end_ms})">
                    <i class="fa-solid fa-circle-play"></i>
                </button>
            </td>
        `;
        subtitleTableBody.appendChild(tr);
    });
}

// Play only selected video segment
let activeVideoSyncHandler = null;
function playSubtitleSegment(startMs, endMs) {
    editorVideoPlayer.currentTime = startMs / 1000;
    editorVideoPlayer.play();
    
    if (activeVideoSyncHandler) {
        editorVideoPlayer.removeEventListener("timeupdate", activeVideoSyncHandler);
    }
    
    activeVideoSyncHandler = () => {
        if (editorVideoPlayer.currentTime >= endMs / 1000) {
            editorVideoPlayer.pause();
            editorVideoPlayer.removeEventListener("timeupdate", activeVideoSyncHandler);
            activeVideoSyncHandler = null;
        }
    };
    
    editorVideoPlayer.addEventListener("timeupdate", activeVideoSyncHandler);
}

// Convert Milliseconds to HH:MM:SS.mmm
function msToTimeStr(ms) {
    const hours = Math.floor(ms / 3600000);
    const minutes = Math.floor((ms % 3600000) / 60000);
    const seconds = Math.floor((ms % 60000) / 1000);
    const milliseconds = ms % 1000;
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}.${milliseconds.toString().padStart(2, '0')}`;
}

// Convert HH:MM:SS.mmm to Milliseconds
function timeStrToMs(str) {
    const match = str.match(/(\d+):(\d+):(\d+)(?:\.(\d+))?/);
    if (!match) return 0;
    const h = parseInt(match[1]);
    const m = parseInt(match[2]);
    const s = parseInt(match[3]);
    const ms = match[4] ? parseInt(match[4].padEnd(3, '0').slice(0, 3)) : 0;
    return h * 3600000 + m * 60000 + s * 1000 + ms;
}

// HTML Escaping
function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Start Dubbing & final video composition (fetch POST Stream reading)
async function startDubbingPipeline() {
    // Collect edited subtitles from grid
    const subsPayload = [];
    const rows = subtitleTableBody.querySelectorAll("tr");
    
    let timeParseError = false;
    
    rows.forEach(row => {
        const index = parseInt(row.querySelector(".subtitle-index").textContent);
        const startVal = row.querySelector(".sub-start-input").value.trim();
        const endVal = row.querySelector(".sub-end-input").value.trim();
        const textVal = row.querySelector(".sub-trans-input").value.trim();
        
        const start_ms = timeStrToMs(startVal);
        const end_ms = timeStrToMs(endVal);
        
        if (start_ms >= end_ms && !timeParseError) {
            timeParseError = true;
            showToast(`Lỗi: Dòng ${index} có thời gian bắt đầu lớn hơn hoặc bằng thời gian kết thúc!`);
            row.style.background = "rgba(239, 68, 68, 0.1)";
        } else {
            row.style.background = "transparent";
        }
        
        subsPayload.push({
            index: index,
            start_ms: start_ms,
            end_ms: end_ms,
            original_text: row.querySelector(".sub-text-orig").textContent,
            translated_text: textVal
        });
    });
    
    if (timeParseError) return;

    editorVideoPlayer.pause();
    switchState(processingState);
    resetPipelineFlowchart();
    consoleBody.innerHTML = "";
    pipelineTitle.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang lồng tiếng & ghép video...';
    
    // Mark previous steps as success
    document.getElementById("step_init").className = "flow-step success";
    document.getElementById("step_extract").className = "flow-step success";
    document.getElementById("step_transcribe").className = "flow-step success";
    
    const flowLines = document.querySelectorAll(".flow-line");
    if (flowLines.length >= 2) {
        flowLines[0].className = "flow-line success";
        flowLines[1].className = "flow-line success";
    }
    
    document.getElementById("step_assemble").className = "flow-step active";
    logToConsole("Khởi chạy luồng lồng tiếng và mix âm thanh...", "info");
    processingProgressBar.style.width = "40%";

    const payload = {
        video_path: currentVideoPath,
        subtitles: subsPayload,
        original_vol: parseFloat(originalVol.value),
        dub_vol: parseFloat(dubVol.value),
        burn_subtitles: burnSubtitles.checked,
        tts_engine: ttsEngine.value,
        voice_name: voiceName.value,
        base_speed: parseFloat(baseSpeed.value),
        match_duration: matchDuration.checked
    };

    try {
        // Since EventSource doesn't support POST, we fetch and parse the stream reader manually!
        const response = await fetch("/api/dub/progress", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error("Không thể khởi động luồng lồng tiếng.");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop(); // keep last chunk in buffer

            for (const line of lines) {
                if (line.trim().startsWith("data: ")) {
                    const data = JSON.parse(line.trim().slice(6));
                    
                    if (data.step === "tts") {
                        if (data.status === "processing") {
                            logToConsole(data.message, "system");
                            // Scale progress bar based on tts steps
                            let currentW = parseFloat(processingProgressBar.style.width);
                            if (currentW < 75) {
                                processingProgressBar.style.width = `${currentW + 0.5}%`;
                            }
                        } else if (data.status === "done") {
                            logToConsole(data.message, "success");
                            processingProgressBar.style.width = "80%";
                        }
                    } 
                    else if (data.step === "merge") {
                        if (data.status === "processing") {
                            logToConsole(data.message, "system");
                            processingProgressBar.style.width = "88%";
                        } else if (data.status === "done") {
                            document.getElementById("step_assemble").className = "flow-step success";
                            const flowLines = document.querySelectorAll(".flow-line");
                            if (flowLines.length >= 3) flowLines[2].className = "flow-line success";
                            logToConsole(data.message, "success");
                            processingProgressBar.style.width = "100%";
                            
                            // Dubbing and Merging finished! Reveal preview panel
                            setTimeout(() => {
                                revealCompletePanel(data.preview_url, data.absolute_path);
                            }, 1000);
                        }
                    } 
                    else if (data.step === "error") {
                        logToConsole(data.message, "error");
                        showToast("Lỗi xử lý lồng tiếng.");
                        document.getElementById("step_assemble").className = "flow-step error";
                    }
                }
            }
        }
    } catch (e) {
        logToConsole(`Lỗi kết nối lồng tiếng: ${e.message}`, "error");
        showToast("Lỗi hệ thống lồng tiếng.");
        document.getElementById("step_assemble").className = "flow-step error";
    }
}

// Show completed preview panel
function revealCompletePanel(previewUrl, absolutePath) {
    switchState(completeState);
    finalVideoPlayer.src = previewUrl;
    finalVideoPath.textContent = absolutePath;
    downloadVideoBtn.href = previewUrl;
}
