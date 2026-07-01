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

TranslateDub AI resolves the Gemini API key and Google Cloud service-account JSON from
environment variables first (`TRANSLATEDUB_GEMINI_KEY` / `GEMINI_API_KEY`, and
`TRANSLATEDUB_GOOGLE_CLOUD_CREDENTIALS` / `GOOGLE_APPLICATION_CREDENTIALS`), then from
`~/.translatedub/config.json`. This is the same model used by `gh`, `aws`, and `npm`.

The config file is created with owner-only permissions (`0o600`), inside a `0o700`
directory. On-disk secrets are plaintext by design: encrypting a local file without a
user passphrase is obfuscation, not security. A future opt-in passphrase mode may add
real encryption.

The configuration API returns only non-secret settings plus boolean "configured" flags.
It never returns the stored Gemini API key or Google Cloud service-account JSON. The
local web server binds to `127.0.0.1` and rejects non-local requests.

Never commit `config.json`, service-account JSON, API keys, temporary videos, or
generated media. See `.gitignore`.

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

TranslateDub AI lấy Gemini API key và Google Cloud service-account JSON theo thứ tự:
biến môi trường trước (`TRANSLATEDUB_GEMINI_KEY` / `GEMINI_API_KEY`, và
`TRANSLATEDUB_GOOGLE_CLOUD_CREDENTIALS` / `GOOGLE_APPLICATION_CREDENTIALS`), sau đó là
file `~/.translatedub/config.json`. Đây là cách `gh`, `aws`, `npm` vẫn làm.

File config được tạo với quyền chỉ chủ máy đọc/ghi (`0o600`) trong thư mục `0o700`.
Secret lưu dạng plaintext là chủ ý: mã hóa file cục bộ mà không có passphrase của người
dùng chỉ là che mắt, không phải bảo mật thật. Sau này có thể thêm chế độ mã hóa bằng
passphrase (tùy chọn).

API cấu hình chỉ trả thiết lập không nhạy cảm và boolean "đã cấu hình", không bao giờ
trả key/JSON đã lưu. Server web chỉ nghe ở `127.0.0.1` và từ chối request không phải cục bộ.

Không commit `config.json`, service-account JSON, API key, video tạm, hay media đã tạo.
Xem `.gitignore`.
