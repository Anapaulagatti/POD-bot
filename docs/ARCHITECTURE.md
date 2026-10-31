# Kiến trúc hiện hành · PODBot Studio 1.0 Preview

```text
CustomTkinter GUI tiếng Việt (modern_app.py) / CLI
  ├─ provider_catalog.py  →  Cloudflare, Hugging Face, Gemini, OpenAI, Replicate, fal.ai, Stability
  ├─ importer.py          →  Nhập file PNG/JPEG/WebP không gọi API ảnh
  ├─ seo.py               →  SEO offline hoặc Gemini (JSON giới hạn 2MB)
  ├─ providers.py         →  Cloudflare API (JSON giới hạn 32MB), Hugging Face
  ├─ http_utils.py        →  đọc JSON giới hạn kích thước, không echo dữ liệu nhạy cảm
  ├─ pipeline.py          →  ảnh gốc + compose_print + fingerprint v2 + manifest JSON
  ├─ processing.py        →  compose_print chung, rembg Python/công cụ ngoài, Real-ESRGAN ngoài
  ├─ audit.py             →  CHÍNH SÁCH QC DUY NHẤT + fingerprint gray/alpha
  ├─ quality.py           →  adapter tương thích các bản cũ, không có ngưỡng riêng
  ├─ publishing.py        →  quyền thương mại + QC + approved + CSV + manual uploaded
  └─ storage.py           →  ghi manifest atomic, sửa SEO/ảnh sẽ reset duyệt cũ
```

- Mọi file in mới và được xử lý lại sử dụng cùng `compose_print`: crop alpha, lề 7%, PNG 5000×5500. Việc resize không tạo thêm chi tiết bản in.
- Fingerprint `v2:` sử dụng dHash nền xám kèm alpha. Hash 16 ký tự cũ (v1) không so với v2, cũng không được dùng để khẳng định trùng. Có thể reprocess để tái tính hash trên thiết kế cũ.
- `audit_image` là nguồn duy nhất của bảng kích thước canvas và các check. `quality.py` giữ API cũ nhưng chỉ chuyển đổi kết quả audit.
- RemBg `.[bg]` có thể tự tải weights khi người dùng chủ động chọn tách nền. EXE thông thường không nhúng weights/các thư viện nặng.
- Không lưu key API vào source/manifest; chỉ lưu vào kho khóa OS sau xác nhận của người dùng. SQLite lưu lượt gọi có thể tính phí mỗi provider mỗi ngày trước khi gửi API và không tự thanh toán/fallback/retry. Không tự động đăng sàn hoặc vượt CAPTCHA.
- Không có OCR, SQLite queue, giới hạn USD chính xác theo provider, installer, code-signing hoặc lockfile đầy đủ. `--onefile --windowed` có thể bị antivirus chặn; bản production tương lai nên hỗ trợ `--onedir`.
- CI trên Windows chạy pytest, Ruff, PyInstaller và smoke-check tồn tại EXE; chưa kiểm tra GUI thủ công ở mọi DPI.

Xem [README](../README.md) và [chính sách xuất bản](PUBLISHING_POLICY.md).
