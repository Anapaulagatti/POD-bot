# Changelog

## 1.0.0rc3 · 1.0 Preview 3 (31/10/2026)
- Tách nền màu phẳng bằng Pillow flood-fill từ mép, không cần model/rembg trong EXE.
- Ô bật/tắt thêm gợi ý nền trắng phẳng vào prompt AI, vẫn lưu prompt gốc.
- Lệnh `podbot rehash` để cập nhật hash v1 từ source.png, giữ nguyên bản quyền/SEO/duyệt.
- Cache session rembg trong phiên, không khởi tạo lại cùng model mỗi ảnh.
- Tính giới hạn API theo ngày local trên Windows; cảnh báo env override.
- Thêm workflow GitHub Release theo tag v*, SHA256, onedir và onefile, pip-audit và snapshot dependency cho release.
- OCR/SQLite task queue/installer/code signing/live paid API tests vẫn ở roadmap.


## 1.0.0rc2 · 1.0 Preview 2
- SQLite bảo vệ lượt gọi API có thể tính phí theo provider, mặc định 3 lần/ngày; không cam kết giới hạn USD.
- Windows Credential Manager qua keyring, chỉ lưu/khôi phục/xóa API key khi người dùng chủ động chọn.
- Ghi nhận lượt trước HTTP để tránh tự retry sau lỗi mạng.

## 1.0.0rc1 (31/10/2026) · Preview 1
- Khắc phục white-on-transparent duplicate hash bằng fingerprint v2, giữ lại manifest cũ.
- Hợp nhất QC vào audit.py, quality.py chỉ là lớp tương thích.
- Chuẩn hóa pipeline mới và xử lý lại ảnh bằng compose_print.
- Hỗ trợ rembg Python extra opt-in, giới hạn JSON Cloudflare/Gemini.
- Cải thiện lỗi OpenAI HTTP 400, chuyển README và kiến trúc về tiếng Việt.

**Lịch sử bên dưới giữ nguyên tên 4.x của các bản thử nghiệm trước khi chuyển sang cách đặt phiên bản preview.**

## 4.1.0 (2026-10-31 · Vietnamese desktop UI)
- Thay giao diện desktop mặc định bằng CustomTkinter MIT, tông xanh than/xanh ngọc và thanh điều hướng trái.
- 5 màn hình tiếng Việt: Tổng quan, Sáng tạo AI, Thư viện thiết kế, Xu hướng, Cài đặt API.
- Thêm dashboard số liệu, thư viện có ảnh xem trước và thao tác quản lý/duyệt từng sản phẩm.
- Giữ lại model marketplace, import ảnh local, SEO, preflight, xử lý ảnh, preview màu áo và mockup, quy trình đăng thủ công an toàn.
- Bổ sung --collect-all customtkinter cho GitHub Actions/PyInstaller one-file Windows và tài liệu tiếng Việt.
- Còn cần kiểm thử giao diện thực tế trên Windows/DPI, không tuyên bố EXE đã được ký số.

## 4.0.0 (2026-10-31, provider marketplace preview)
- Added 14 manually selectable image models: Gemini 3.1 Flash/Lite, 3 Pro, Nano Banana 2.1; OpenAI GPT Image 2.5 Flare/Sunburst; Replicate FLUX; fal.ai FLUX2/Z-Image; Stability Core/Ultra; retained Cloudflare/HF.
- Paid model consent in the desktop UI and --paid-ok for CLI, no silent provider fallbacks.
- Added personal PNG/JPEG/WebP import without image API usage.
- Added URL/size validation for remote image results, API response contract tests with HTTP mocks.
- Added provider API reference, 15-source licensing research and phased roadmap.
- No claim of live paid API coverage, signed release, automatic marketplace publishing or unlimited free-tier access.


## 0.3.0 (2026-10-31)
- Optional external rembg/Real-ESRGAN processing; safe alpha-cropped 5000 x 5500 PNG output.
- Four-color apparel previews and image audit with approval-blocking errors.
- User-editable blocklist, dHash fingerprint stored, human-rights confirmation and approved-only manual export.
- Explicit local upload confirmation, state invalidation after metadata or image changes.
- Expanded automated Windows tests and docs for marketplace requirements and third-party license caveats.

## 0.2.0
- Google Trends RSS, print preflight, basic T-shirt preview, editable SEO and local ECC developer skills.

## 0.1.0
- Initial Windows desktop, image providers, SEO and JSON manifest based review queue.
