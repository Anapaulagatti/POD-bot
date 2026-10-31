# Hướng dẫn cài đặt, chạy thử và build PODBot.exe

## Repository

Mã nguồn chính thức của dự án đang được phát triển trong:
https://github.com/Anapaulagatti/POD-bot

Đây là MVP đầu tiên. Công cụ **chưa tự đăng sản phẩm** lên Redbubble hoặc TeePublic; thao tác đăng bán là thủ công có xác nhận.

## Cài và chạy local trên Windows

Cài Python 3.11+ rồi mở PowerShell:

```powershell
git clone https://github.com/Anapaulagatti/POD-bot.git
cd POD-bot
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[hf,dev]"
python -m pytest -q
python -m podbot
```

Trước khi tạo hình, điền Cloudflare Account ID và token trong tab API Settings. Dùng Gemini SEO chỉ khi bạn có API key hợp lệ. Bot không lưu token.

## Tạo file EXE

Có hai cách:

**Cách 1: GitHub Actions (không cần tự build trên máy).**

1. Mở https://github.com/Anapaulagatti/POD-bot/actions
2. Chọn workflow **Validate and build Windows executable**.
3. Chờ kết quả workflow chạy trên Windows runner.
4. Nếu thành công, tải artifact **PODBot-windows-exe** từ workflow run.
5. Kiểm tra file EXE trên máy Windows, nên quét virus và lưu ý EXE chưa được ký số.

**Cách 2: Tự build trên Windows.**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

Nếu kiểm thử và build thành công, đầu ra sẽ ở `dist/PODBot.exe`.

## Những gì chưa phải tính năng sản xuất

- Ảnh AI có thể chưa có nền thực sự trong suốt.
- Chuyển kích thước PNG lên 4500 x 5400 không tự tạo thêm chi tiết.
- SEO hiện là bản nháp cần kiểm duyệt; chưa phải số liệu trend thật.
- Không có bot tự đăng bài, đăng nhập sàn, lưu mật khẩu, hoặc vượt CAPTCHA.

Không chia sẻ token, cookie, mật khẩu GitHub, Redbubble hay TeePublic trong issue hoặc commit.

## Tính năng bổ sung nhánh phát triển 0.2

- Vào **Trend Research**, chọn quốc gia rồi bấm **Fetch public trends** để xem danh sách truy vấn phổ biến, nguồn Google RSS. Không được tự động dùng nhãn hiệu, người nổi tiếng, tên phim vào thiết kế để bán.
- Ở **Publishing Queue**, chọn thiết kế và sàn, bấm **Preflight** để kiểm tra kích thước, diện tích hình có alpha và cảnh báo nguồn ảnh bị phóng to; bấm **T-shirt mockup** để xem bố cục mô phỏng trên áo.
- CLI: `podbot trends --country US --limit 10`, `podbot preflight --id DESIGN_ID --platform teepublic`, `podbot mockup --id DESIGN_ID`.
- Kiểm tra tài liệu kích thước theo sàn trong [MARKETPLACE_REQUIREMENTS.md](MARKETPLACE_REQUIREMENTS.md).
- ECC chỉ được thêm như skill phát triển **project-local**. Muốn cài toàn bộ plugin vào Claude Code, đọc [ECC_INTEGRATION.md](ECC_INTEGRATION.md) và tránh cài song song hai phương thức trùng nhau.

## Release 0.3

- **Process PNG**: tùy chọn tách nền bằng rembg hoặc upscale Real-ESRGAN đã cài riêng, hoàn toàn không bắt buộc. Chọn No cho bước tách nền/upscale nếu muốn crop và tạo canvas bằng Pillow.
- **Preflight** báo PASS/WARN/FAIL, chỉ duyệt thiết kế không có FAIL và đã xác nhận quyền thương mại.
- **4 colors** tạo ảnh xem trước trên áo trắng/đen/navy/xám.
- **Edit Blocklist** mở file từ khóa do bạn tự quản lý. Đây không phải cơ sở dữ liệu thương hiệu chính thức.
- **Approve** kiểm tra quyền tác giả + chất lượng; **Export CSV** chỉ chứa thiết kế approved; **Mark Uploaded** chỉ ghi trạng thái sau khi bạn đã đăng thủ công trên sàn.
- Xem chi tiết tại [PUBLISHING_POLICY.md](PUBLISHING_POLICY.md).
