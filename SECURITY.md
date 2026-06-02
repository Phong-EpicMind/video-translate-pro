# Security Policy

## Supported Versions

Security fixes are handled on the default branch, `main`, until the project adopts versioned release support windows.

## Reporting A Vulnerability

Do not open a public issue for secrets, credential leaks, private media exposure, or exploitable vulnerabilities.

Report privately through one of these channels:

* GitHub private vulnerability reporting, if enabled for this repository.
* A direct maintainer contact listed in the GitHub repository profile.

Please include:

* A concise description of the issue.
* Reproduction steps or affected files.
* Impact and whether credentials, local files, generated media, or user privacy can be exposed.
* The app version or Git commit if known.

## Secret Handling

TranslateDub AI stores Gemini API keys and Google Cloud Service Account JSON in macOS Keychain under the `com.phongho.translatedubai` service.

The local `~/.translatedub_ai/config.json` file is reserved for non-secret preferences and is written with restrictive file permissions. If an older config file contains secrets, the app migrates them to Keychain and rewrites the file without those secret fields.

The configuration API returns only non-secret settings plus boolean configured flags. It does not return stored Gemini API keys or Google Cloud Service Account JSON.

Never commit local `config.json`, Google Cloud service account JSON, API keys, temporary videos, generated audio, `.dmg`, `.app`, `dist/`, `build/`, `bin/`, or release artifacts.

---

## Tiếng Việt

### Phiên bản được hỗ trợ

Bản vá bảo mật được sửa trên branch mặc định `main` cho đến khi dự án có chính sách hỗ trợ theo từng version.

### Báo cáo lỗ hổng bảo mật

Không tạo public issue nếu vấn đề liên quan đến secret, rò rỉ credential, file media riêng tư, hoặc lỗ hổng có thể khai thác.

Hãy báo cáo riêng qua:

* GitHub private vulnerability reporting, nếu repo đã bật tính năng này.
* Kênh liên hệ maintainer được công bố trên GitHub profile.

Nên cung cấp:

* Mô tả ngắn gọn vấn đề.
* Bước tái hiện hoặc file bị ảnh hưởng.
* Tác động, gồm khả năng lộ credential, file cục bộ, media đã tạo, hoặc dữ liệu riêng tư.
* Version app hoặc commit Git nếu biết.

### Xử lý secret

TranslateDub AI lưu Gemini API key và Google Cloud Service Account JSON trong macOS Keychain với service `com.phongho.translatedubai`.

File `~/.translatedub_ai/config.json` chỉ dùng cho cấu hình không nhạy cảm và được ghi với quyền hạn chế. Nếu file config cũ có chứa secret, app sẽ migrate secret sang Keychain và ghi lại file mà không còn các trường secret.

API cấu hình chỉ trả về thiết lập không nhạy cảm và có boolean cho biết đã cấu hình hay chưa. API này không trả Gemini API key hoặc Google Cloud Service Account JSON đã lưu.

Không commit `config.json`, Service Account JSON, API key, video tạm, audio đã tạo, `.dmg`, `.app`, `dist/`, `build/`, `bin/`, hoặc release artifacts.
