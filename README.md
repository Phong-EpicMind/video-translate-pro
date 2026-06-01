# TranslateDub AI - Trình dịch thuật & Lồng tiếng Video macOS Độc lập
### *World-Class Native macOS Desktop Video Translation & Dubbing Suite Integrated with Google AI APIs*

[![CI](https://github.com/Phong-EpicMind/video-translate-pro/actions/workflows/ci.yml/badge.svg)](https://github.com/Phong-EpicMind/video-translate-pro/actions/workflows/ci.yml)
[![Security Scan](https://github.com/Phong-EpicMind/video-translate-pro/actions/workflows/security.yml/badge.svg)](https://github.com/Phong-EpicMind/video-translate-pro/actions/workflows/security.yml)
[![License: MIT](https://img.shields.io/badge/Source%20License-MIT-green.svg)](LICENSE)

---

**TranslateDub AI** là một ứng dụng Desktop Native cao cấp dành riêng cho macOS, được thiết kế để đơn giản hóa hoàn toàn quy trình dịch thuật, biên tập phụ đề và lồng tiếng video đa ngôn ngữ. Ứng dụng hoạt động hoàn toàn cục bộ, kết hợp giao diện **Glassmorphism hiện đại** và sức mạnh vượt trội của các mô hình **Google AI thế hệ mới (Gemini 2.5 Flash & Google Cloud TTS)**.

> [!IMPORTANT]
> **Cam kết Bảo mật Tuyệt đối (Security-First Standard):** Ứng dụng đáp ứng các tiêu chuẩn bảo mật hệ thống nghiêm ngặt. Khóa API và tài liệu cấu hình được mã hóa hiển thị và khóa chặt bằng phân quyền Unix (`chmod 600` / `chmod 700`) trực tiếp trên máy Mac của bạn. Không bao giờ lưu trữ hoặc gửi thông tin cấu hình lên bất kỳ máy chủ bên thứ ba nào.

---

## 🌟 Tính Năng Nổi Bật (Key Features)

### 1. Trải nghiệm Glassmorphic Premium UI
* Giao diện Dark Mode huyền ảo với các khối kính mờ và gradient phát sáng mượt mà.
* Hỗ trợ **Kéo & Thả (Drag-and-Drop)** file video hoặc nhập đường dẫn cục bộ trên máy Mac siêu nhanh.
* **Real-time Pipeline Tracker:** Theo dõi tiến trình xử lý từng khâu thông qua bảng hiển thị Console Log thời gian thực chi tiết.

### 2. Trình dịch thuật Google AI Siêu tốc
* Tự động trích xuất âm thanh chất lượng cao bằng `ffmpeg` thông qua dọn dẹp môi trường dynamic link an toàn.
* Nhận dạng giọng nói (STT) và Dịch thuật thông minh trong một luồng đơn lẻ bằng **Gemini 2.5 Flash** (với khả năng tự động chia đoạn thông minh cho video dài).
* Cơ chế **Auto-Retry & Model Fallback** thông minh vượt qua các đợt nghẽn mạng của Google API bằng cách tự động thử lại và hạ cấp xuống `gemini-2.0-flash` hoặc `gemini-2.0-flash-lite` mà không làm treo app.

### 3. Biên tập Phụ đề Tương tác (Interactive Subtitle Editor)
* Trình xem trước và biên tập phụ đề trực quan với bảng hiển thị song ngữ (Gốc - Dịch).
* **Đồng bộ hóa trình phát (Player Sync):** Nút phát thử từng dòng phụ đề tự động nhảy trình phát video cục bộ đến đúng mốc thời gian (timestamp) để kiểm tra ngữ điệu.

### 4. Tổng hợp Giọng nói Siêu thực (Premium TTS Engine)
* Tích hợp 12+ giọng đọc **Google Cloud TTS Premium** phân chia rõ ràng theo Vùng miền (Bắc/Nam) và Giới tính (Nam/Nữ).
* Thuật toán **Khớp thời lượng thoại (Match Duration)** và điều chỉnh tốc độ chuẩn gốc (`speaking_rate` từ 0.8x đến 1.25x), giữ trọn vẹn cao độ tự nhiên, loại bỏ hoàn toàn giọng robot kim loại.

### 5. Cấu hình Xuất bản tùy chỉnh & Thiết kế Độc lập
* Tích hợp hộp chọn **Native macOS Finder Folder Picker** giúp nhấp chọn thư mục lưu video bất kỳ trên máy Mac.
* Khóa bảo mật API Key toàn diện thông qua phân quyền tệp tin và mặt nạ hiển thị WebKit (`-webkit-text-security`).

---

## 🛠️ Công Nghệ Sử Dụng (Technology Stack)

* **Core Backend:** Python 3.11, FastAPI (Uvicorn daemon)
* **Desktop Wrapper:** PyWebview (Cocoa Native WebKit - WKWebView)
* **AI & Cloud Engine:** Google GenAI SDK (Gemini 2.5 Flash), Google Cloud Text-to-Speech API, gTTS
* **Audio/Video Processing:** FFmpeg, FFprobe, Pydub
* **Frontend UI:** HTML5, Vanilla CSS3 (Glassmorphism), Vanilla JavaScript ES6

---

## 📦 Hướng dẫn Cài đặt & Khởi chạy (Installation & Setup)

### 🚀 Cách 1: Sử dụng File ảnh đĩa .DMG (Khuyên dùng cho người dùng cuối)
Nếu bạn là khán giả hoặc muốn sử dụng ngay ứng dụng mà không cần quan tâm đến code hay cài đặt môi trường lập trình phức tạp:
1. Tải về file **`TranslateDub_AI_macOS.dmg`** từ mục Releases của GitHub hoặc link chia sẻ.
2. Nhấp đúp mở file `.dmg`, **kéo thả biểu tượng TranslateDub AI vào thư mục Applications** ở ngay bên cạnh.
3. **Mở ứng dụng lần đầu:** Click chuột phải (hoặc nhấn phím `Control` + click) vào ứng dụng trong thư mục `Applications`, chọn **Open**, rồi nhấp **Open** ở hộp xác nhận để vượt qua cảnh báo macOS Gatekeeper (chỉ cần thực hiện 1 lần duy nhất).

---

### 💻 Cách 2: Cài đặt cho lập trình viên & Phát triển (Local Setup)

### Yêu cầu hệ thống (Prerequisites)
1. Máy Mac chạy chip **Apple Silicon (M1/M2/M3/M4)** hoặc **Intel**.
2. Đã cài đặt **FFmpeg** qua Homebrew (chỉ cần thiết cho môi trường code cục bộ, bản đóng gói `.dmg` đã tích hợp sẵn):
   ```bash
   brew install ffmpeg
   ```

### 1. Cài đặt môi trường phát triển cục bộ
1. Clone mã nguồn về máy:
   ```bash
   git clone <your-repository-url>
   cd video-translate-pro
   ```
2. Tạo Virtual Environment và cài đặt thư viện:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

### 2. Đóng gói ứng dụng Desktop macOS độc lập
Để tự đóng gói mã nguồn thành ứng dụng `.app` độc lập trên máy Mac của bạn:
```bash
./venv/bin/pyinstaller -y --noconsole --name "TranslateDub AI" \
  --icon "static/icon.icns" \
  --add-data "templates:templates" \
  --add-data "static:static" \
  --add-data "LICENSE:." \
  --add-data "THIRD_PARTY_NOTICES.md:." \
  --add-data "FFMPEG_SOURCE_OFFER.md:." \
  --add-binary "bin/ffmpeg:bin" \
  --add-binary "bin/ffprobe:bin" \
  desktop.py
```
Sau khi hoàn tất, tệp cài đặt **TranslateDub AI.app** sẽ xuất hiện tại thư mục `dist/`. Bạn có thể sao chép nó trực tiếp vào thư mục `/Applications/` của macOS và ghim vào thanh Dock.

---

## 🔒 Tiêu Chuẩn Bảo Mật Quốc Tế (Security & Privacy Standards)

Ứng dụng tuân thủ nghiêm ngặt các quy tắc bảo mật của hệ thống macOS:
1. **Phân quyền UNIX Tối thiểu (chmod 600 / 700):**
   * Thư mục dữ liệu ứng dụng `~/.translatedub_ai/` được gán quyền `chmod 700` (chỉ chủ tài khoản được truy cập).
   * File cấu hình khóa API `config.json` được gán quyền `chmod 600` (chỉ chủ tài khoản được đọc/ghi), ngăn chặn triệt để các mã độc cục bộ đọc trộm.
2. **WebKit Multiline Masking:** Ô dán Service Account JSON của Google Cloud được che giấu bằng mặt nạ chấm đĩa bảo mật nguyên bản của macOS Safari engine, ngăn chặn rò rỉ khóa khi chia sẻ màn hình.
3. **Môi trường cách ly Git (.gitignore):** Tệp cấu hình chứa API Key cục bộ và các thư mục video tạm được thêm vào danh sách bỏ qua của Git để ngăn chặn tuyệt đối việc vô tình tải dữ liệu nhạy cảm lên GitHub.

---

## 📄 Bản quyền & Thông báo bên thứ ba (License & Third-Party Notices)

### Giấy phép (License)
* **Mã nguồn (Source Code):** Toàn bộ mã nguồn gốc của dự án **TranslateDub AI** được phân phối tự do dưới giấy phép **[MIT License](LICENSE)**. Bạn hoàn toàn được phép sử dụng, sao chép, sửa đổi, tích hợp hoặc phân phối mã nguồn này cho các mục đích của mình.
* **Bản đóng gói (.dmg Bundle):** Bản đóng gói cài đặt sẵn có trên macOS chứa các thành phần nhị phân của bên thứ ba (như FFmpeg/FFprobe). Các thành phần này tuân thủ các giấy phép nguồn mở tương ứng của chúng (chủ yếu là GPL-3.0). Chi tiết giấy phép đầy đủ của bên thứ ba được ghi nhận tại **[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)**.

---

### Thông báo bên thứ ba (Third-Party Notices)
Chi tiết về bản quyền và nguồn gốc của các thư viện, công cụ được tích hợp trong dự án (bao gồm ghi nhận công lao của dự án truyền cảm hứng **pyVideoTrans** và các tệp tĩnh **FFmpeg/FFprobe** theo chuẩn GPL-3.0) được kê khai đầy đủ tại tệp tin **[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)**. Nếu phát hành bản `.dmg` kèm FFmpeg/FFprobe, xem thêm **[FFMPEG_SOURCE_OFFER.md](FFMPEG_SOURCE_OFFER.md)** để chuẩn bị nguồn tương ứng hoặc written offer cho FFmpeg.

---
*Phát triển độc lập bởi Phong Ho. Tích hợp các công nghệ Google AI thế hệ mới.*
