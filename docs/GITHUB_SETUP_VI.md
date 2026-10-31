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
