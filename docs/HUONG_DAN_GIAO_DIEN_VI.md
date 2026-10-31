# Hướng dẫn PODBot Studio 4.1 · Giao diện tiếng Việt

Phiên bản này chuyển giao diện mặc định sang tiếng Việt với kiểu thiết kế tối hiện đại, menu trái và các màn hình có thanh cuộn. Mã nguồn và cài đặt API vẫn chạy local trên Windows.

## 1. Khởi động

1. Vào tab **Actions** của repository, tải artifact `PODBot-windows-exe` tại build có trạng thái **Success**.
2. Giải nén ZIP, mở `PODBot.exe` trên Windows 10/11.
3. Ở lần mở đầu tiên, chọn **Cài đặt API** nếu muốn tạo hình AI. Chỉ nhập API key của nền tảng bạn dùng. Ứng dụng **không lưu key** sau khi đóng.
4. Nếu bạn đã có ảnh thiết kế, chọn **Sáng tạo AI → Nhập ảnh từ máy (0 phí API)**, không cần API key.

## 2. Năm màn hình chính

**Tổng quan:** Xem số thiết kế đã lưu, số đã được duyệt và số đã đăng lên sàn. Bấm `Tạo thiết kế mới` để chuyển thẳng sang Studio.

**Sáng tạo AI:** Mô tả thiết kế → chọn chủ đề, từ khóa, model Gemini/OpenAI/Replicate/fal/Stability/Cloudflare/HF → chọn SEO offline hoặc Gemini SEO → bấm `Tạo bằng AI`. Các dịch vụ có thể tính tiền đều hỏi xác nhận trước khi gửi yêu cầu; không tự chuyển model khi lỗi. Có thể nhập ảnh PNG/JPEG/WebP từ máy.

**Thư viện thiết kế:** Chọn thiết kế ở danh sách, kiểm tra ảnh nguồn, tên sản phẩm và trạng thái Redbubble/TeePublic. Các nút hỗ trợ:
- **Xem PNG:** mở file in.
- **Chỉnh SEO:** cập nhật tiêu đề, mô tả và tags; các lần duyệt trước bị vô hiệu nếu nội dung thay đổi.
- **Kiểm tra chất lượng:** xác định nền, kích thước, vùng in, chạm mép và cảnh báo khác.
- **Xử lý lại ảnh:** crop, làm file in, tùy chọn rembg/Real-ESRGAN cài riêng.
- **Xem màu áo:** ảnh so sánh trên bốn màu nền.
- **Mockup áo thun:** hình áo minh họa dùng để kiểm tra bố cục.
- **Duyệt thiết kế:** yêu cầu xác nhận quyền thương mại và vượt kiểm tra chất lượng.
- **Mở trang đăng:** mở trang chính thức khi thiết kế đã duyệt, không tự upload.
- **Đã đăng:** chỉ xác nhận sau khi bạn đăng và kiểm tra trên tài khoản bán hàng.
- **Xuất CSV đã duyệt:** xuất thông tin thiết kế để điền thủ công trên sàn.

**Xu hướng:** Chọn thị trường (US, GB, JP...) và tải nguồn RSS Google Trends. Chủ đề đang nổi không mặc nhiên an toàn về bản quyền.

**Cài đặt API:** Nhập các API key nếu dùng. Danh sách thông tin bí mật không ghi vào file cấu hình. Có thể mở thư mục dữ liệu và sửa blocklist từ khóa cần cảnh báo.

## 3. An toàn và dữ liệu cũ

- Thiết kế, ảnh và SEO dùng chung vị trí dữ liệu các phiên bản trước, mặc định `Documents/PODBot/designs`.
- Ảnh AI có thể chưa có nền trong suốt hoặc độ nét phù hợp. Xem preview và kiểm tra bản in.
- Phần mềm không lưu mật khẩu hay cookies Redbubble/TeePublic; không chạy bot vượt CAPTCHA, không đăng hàng loạt tự động.
- Chi phí gọi API thuộc về tài khoản nhà cung cấp. Không có chế độ miễn phí vô hạn.

## 4. Gỡ lỗi cửa sổ / giao diện

- Nếu mở EXE nhưng font/theme không hiện: tải lại artifact từ lần chạy CI xanh của nhánh `main`, không dùng EXE phiên bản cũ.
- Nếu giao diện quá lớn: điều chỉnh Windows Settings → System → Display → Scale và khởi động lại ứng dụng.
- Nếu không thể tạo ảnh: kiểm tra API key, model hỗ trợ, hạn mức và trang quản lý chi phí nhà cung cấp.
- Nếu giao diện mất nút: phóng lớn cửa sổ; các màn hình có thanh cuộn. Kích thước cửa sổ tối thiểu là 940×660.

Xem [UI_REDESIGN_VI.md](UI_REDESIGN_VI.md) để biết lý do chọn CustomTkinter và đánh giá các repository khác.

**Trạng thái thử nghiệm:** CI kiểm tra source/test/build trên Windows. Chưa thể xác nhận giao diện hoạt động ở mọi DPI/cấu hình Windows và cần thử trực tiếp trên máy người dùng.

## Tách nền nhanh trong EXE Preview 3

Tại **Thư viện → Xử lý lại ảnh**, chọn **Có** ở lựa chọn tách nền phẳng bằng Pillow để thử với ảnh có nền trắng/màu đơn sắc. Sau khi xử lý, xem lại PNG, ảnh trên bốn màu áo, kiểm tra halo/chữ nhỏ và duyệt lại nếu đạt. Với nền nhiều chi tiết, dùng rembg tùy chọn hoặc xử lý bằng phần mềm đồ họa. Tách nền không được tự kích hoạt khi phát sinh phí AI.

Tại **Sáng tạo AI**, bật/tắt ô thêm gợi ý nền trắng phẳng. Với thư viện cũ, CLI `podbot rehash --dry-run` và `podbot rehash` giúp tính lại fingerprint v2 mà không thay đổi trạng thái duyệt.

Hạn mức API tính theo **00:00 giờ local của Windows**; nếu có biến môi trường ghi đè, trang Cài đặt sẽ hiển thị cảnh báo.
