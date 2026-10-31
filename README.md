# PODBot Studio · 1.0 Preview (Giao diện tiếng Việt)

**Ứng dụng Windows local cho Print-on-Demand.** Tạo ảnh AI, chọn nhà cung cấp, nhập PNG/JPEG/WebP riêng không mất phí ảnh, chuẩn hóa PNG, duyệt QC, chỉnh SEO và hỗ trợ đăng Redbubble/TeePublic theo quy trình **do người dùng xác nhận**.

Phiên bản kỹ thuật `1.0.0rc1` (1.0 Preview 1). Đây là bản thử nghiệm, không phải bản sản xuất đã ký mã. Các bản 4.x trước đây chỉ mang ý nghĩa tên bản thử nghiệm và được giữ trong CHANGELOG để tra cứu.

## Bắt đầu trong Windows

1. Trên [GitHub Actions](https://github.com/Anapaulagatti/POD-bot/actions), chọn workflow thành công của nhánh `main`; tải `PODBot-windows-exe`, giải nén và chạy `PODBot.exe`.
2. Mở **Cài đặt API** nếu muốn tạo ảnh AI bằng Cloudflare, Hugging Face, Gemini, OpenAI, Replicate, fal.ai hoặc Stability AI. API key chỉ giữ trong RAM hoặc biến môi trường theo mặc định; có thể chủ động lưu vào kho khóa hệ điều hành.
3. Mở **Sáng tạo AI**, chọn model, prompt và SEO. Với model tính phí, người dùng xác nhận trước; không tự chuyển model và không tự thử lại có phí. Hoặc chọn **Nhập ảnh từ máy**, không dùng API ảnh.
4. Vào **Thư viện thiết kế**, kiểm tra file PNG, sửa SEO, tạo mockup và kiểm tra chất lượng in. Duyệt thương mại sau khi QC đạt và xác nhận quyền sử dụng.
5. Mở trang sàn để tự đăng sản phẩm, sau đó bấm **Đã đăng** nếu thực sự đã kiểm tra trên tài khoản bán.

## Những điểm kỹ thuật hiện có

- **Một bộ QC duy nhất:** `audit.py` xác định kích thước, nền alpha, mép ảnh, vùng in; `quality.py` chỉ là lớp tương thích cũ. Các cảnh báo không thay thế bản in kiểm tra.
- **Một quy tắc chuẩn hóa ảnh:** `compose_print` crop theo vùng alpha và chừa lề 7% cho cả ảnh mới lẫn ảnh xử lý lại. Canvas 5000×5500 và DPI metadata không làm chi tiết gốc sắc nét hơn.
- **Fingerprint v2** kết hợp hash hình trên nền xám và kênh alpha, sửa lỗi mọi chữ trắng trên nền trong suốt bị báo trùng. Hash v1 cũ bị bỏ qua khi dò trùng, dữ liệu cũ vẫn đọc được.
- **Xóa nền tùy chọn:** chạy `rembg` Python hoặc `rembg.exe` cài riêng. Lần chạy đầu tiên có thể tải trọng số AI, chỉ khi người dùng xác nhận.
- **JSON API có giới hạn:** Gemini SEO tối đa 2 MB và Cloudflare ảnh base64 tối đa 32 MB.
- **OpenAI:** tài liệu API công bố các model 2.5 Flare/Sunburst hỗ trợ `background: transparent` cho PNG. Khi HTTP 400, ứng dụng hướng dẫn kiểm tra model/tham số; không tự gọi lại yêu cầu tính phí. Xem [OpenAI Images API](https://developers.openai.com/api/reference/resources/images/methods/generate).

## Cài từ mã nguồn / thêm nền AI

```powershell
git clone https://github.com/Anapaulagatti/POD-bot
cd POD-bot
python -m pip install -e ".[hf,dev]"
python -m pytest -q
python -m ruff check src tests

# Chỉ khi bạn muốn dùng rembg Python:
python -m pip install -e ".[bg]"
```

`.[bg]` chạy với bản Python đã cài dependency. **Không thể pip install thêm vào EXE PyInstaller đã build sẵn**. EXE tiêu chuẩn không có rembg ML runtime, nhưng bạn có thể chọn `rembg.exe` đã cài riêng. Bản có ML tích hợp phải build riêng, kiểm tra VRAM/RAM và giấy phép trọng số.

## Tài liệu

[Hướng dẫn tiếng Việt](docs/HUONG_DAN_GIAO_DIEN_VI.md) · [Kiến trúc](docs/ARCHITECTURE.md) · [Chính sách sàn](docs/PUBLISHING_POLICY.md) · [Các model](docs/PROVIDER_MARKETPLACE_V4.md) · [Nghiên cứu repo](docs/REPOSITORY_RESEARCH_V4.md) · [Lộ trình](docs/ROADMAP_V4.md) · [Lịch sử](CHANGELOG.md)

**Chưa có:** OCR, SQLite jobs + cancel/retry, giới hạn USD chính xác theo provider, lockfile đủ phụ thuộc bắc cầu, installer, ký mã, tự đăng Redbubble/TeePublic. Build `--onefile --windowed` có thể bị antivirus cảnh báo nhầm; phương án `--onedir`/installer cần triển khai và thử nghiệm sau.

## Bảo vệ API trả phí (1.0 Preview 2)

- **Giới hạn lượt gọi:** mặc định tối đa 3 lượt API *có thể tính phí* / nhà cung cấp / ngày (gồm Gemini SEO). SQLite ghi lượt trước khi gửi API, không hoàn lượt khi lỗi mạng vì nhà cung cấp vẫn có thể tính tiền. Trong GUI → **Cài đặt API**, sửa số lượt 0–100. CLI: `podbot api-limit` hoặc `podbot api-limit --set 2`. Biến môi trường `PODBOT_PAID_CALLS_PER_DAY` nếu có sẽ ưu tiên hơn cấu hình lưu.
- **Giới hạn USD:** chưa tính được số tiền chính xác bằng tiền. Quota này không phản ánh bill thực tế; cần đặt ngưỡng chi tiêu tại dashboard nhà cung cấp.
- **Windows Credential Manager:** Chỉ khi bạn bấm **Lưu key vào Windows** và đồng ý, key mới được lưu bằng `keyring`. Nút **Khôi phục key** / **Xóa key đã lưu** hoạt động riêng. Không tự nạp key từ vault khi mở ứng dụng.
