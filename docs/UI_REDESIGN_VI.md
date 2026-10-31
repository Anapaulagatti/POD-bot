# Nâng cấp giao diện PODBot Studio 4.1 · Tiếng Việt

Ngày kiểm tra: 31/10/2026. Dữ liệu giấy phép và hoạt động lấy từ GitHub; khi phân phối phần mềm thương mại cần xác minh lại.

## Khảo sát repository giao diện Python

| Repository | License | Hoạt động kiểm tra | Đánh giá cho PODBot |
| --- | --- | --- | --- |
| [TomSchimansky/CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | MIT | Không archived; có commit 2026 | **Đã chọn.** Bo góc, CTkFrame/CTkButton/CTkScrollableFrame, Windows DPI, có thể thay thế GUI Tkinter cũ mà giữ nguyên các module Python. |
| [israel-dryer/ttkbootstrap](https://github.com/israel-dryer/ttkbootstrap) | MIT (metadata GitHub; phiên bản PyPI gồm third-party licenses) | Có cập nhật 10/2026 | Giải pháp dự phòng tối ưu khi cần ứng dụng nhẹ và gần ttk cổ điển; giao diện ít khác biệt nếu không thiết kế lại cấu trúc. |
| [zhiyiYo/PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) | GPL-3.0 / có giấy phép thương mại | Cập nhật 10/2026 | Rất đẹp kiểu Windows 11 nhưng quy định cấp phép phải được xem xét kỹ; PySide/Qt làm tăng kích thước EXE. Chưa tích hợp. |
| [flet-dev/flet](https://github.com/flet-dev/flet) | Apache-2.0 | Cập nhật 10/2026 | UI responsive tốt, nhưng đòi hỏi đổi runtime, phụ thuộc stack mới và quy trình đóng gói. Để dành cho tái kiến trúc lớn. |
| [pywebview/pywebview](https://github.com/r0x0r/pywebview) | BSD-3-Clause (kiểm tra lại trước khi tích hợp) | Dự án hiện hành | Phù hợp UI HTML/CSS có cảm giác web-app, nhưng cần WebView2/runtime và bảo mật bridge JS. Không cần cho bản local hiện tại. |
| [rdbende/Sun-Valley-ttk-theme](https://github.com/rdbende/Sun-Valley-ttk-theme) | MIT | Ít cập nhật hơn | Phương án thay theme cho Tkinter đơn giản, không giải quyết workflow nhiều trang. |
| [Akascape/CTkMessagebox](https://github.com/Akascape/CTkMessagebox) | CC0-1.0 (theo GitHub metadata) | Ít cập nhật hơn | Có thể bổ sung dialog đẹp đồng bộ về sau; bản 4.1 giữ messagebox chuẩn Tk để tránh thêm package chưa đánh giá. |

Không sao chép code giao diện từ các repository; chỉ sử dụng thư viện CustomTkinter làm dependency có giấy phép MIT.

## Thiết kế được triển khai

**Ngôn ngữ mặc định:** tiếng Việt, các label, menu, mô tả tính năng, trạng thái và hướng dẫn. Prompt sáng tạo bằng tiếng Anh vẫn được giữ làm mẫu để tương thích model quốc tế; metadata SEO bán quốc tế cũng dùng tiếng Anh. Lỗi nguyên bản từ API bên ngoài đôi khi còn tiếng Anh; đây là phần cần bổ sung bản dịch thông báo ở phiên bản tiếp theo.

**Tông màu:** xanh than #0B1220, xanh ngọc #30DBC2, bề mặt #152438, viền #263C54, chữ #F1F7FC. Cỡ chữ giao diện 11–27pt, font Segoe UI có Unicode tiếng Việt; phù hợp Windows High-DPI của CustomTkinter.

**Điều hướng:** thanh bên trái + năm màn hình: Tổng quan, Sáng tạo AI, Thư viện thiết kế, Xu hướng, Cài đặt API. Trang tổng quan hiển thị tổng thiết kế, số đã duyệt, số đã đăng.

**Không bỏ bớt workflow:** tạo ảnh Gemini/OpenAI/Replicate/fal/Stability/Cloudflare/HF, chọn SEO, nhập ảnh local, xem PNG, sửa SEO, kiểm tra chất lượng, chỉnh file in, preview 4 màu, duyệt có xác nhận quyền bán, mở website chính thức, xác nhận đã đăng, xuất CSV đã duyệt và sửa blocklist. Dữ liệu JSON cũ ở ~/Documents/PODBot được dùng lại.

**Tránh khóa UI:** tạo ảnh, nhập file, nghiên cứu xu hướng và xử lý chất lượng qua worker thread; xử lý UI bằng queue và Tk after. Không tự trả phí ngoài model đã chọn, không tự đăng sàn, không lưu API key.

## Lưu ý build Windows EXE

CustomTkinter mang theo các tệp JSON/OTF. Wiki PyInstaller cũ của repo khuyến nghị `--onedir`; các phiên bản PyInstaller sau hỗ trợ `--onefile` nếu gom đủ data files. Vì mục tiêu là **một file EXE**, workflow sử dụng `--onefile --collect-all customtkinter` và kiểm tra artifact trong GitHub Actions. Đây mới là kiểm tra build; phải chạy thủ công trên máy Windows thật để phát hiện lỗi theme/font/hiển thị DPI.

Tài liệu: https://github.com/TomSchimansky/CustomTkinter/wiki/Packaging
Vấn đề thảo luận một file: https://github.com/TomSchimansky/CustomTkinter/issues/1518

## Tiêu chí nghiệm thu khi dùng thực tế

1. EXE khởi động trên Windows 10/11 và hiển thị Unicode tiếng Việt, không bị vỡ chữ.
2. Ở 100%, 125%, 150% DPI, menu và form không che nút; cửa sổ tối thiểu 940×660; có cuộn.
3. Sử dụng API key nhập trong Settings rồi tạo ảnh bằng model được cấp phép. Test API trả phí ngoài CI, chỉ khi người dùng xác nhận.
4. Nhập PNG ẩn phí API, xem ảnh trong thư viện, sửa SEO, preflight và xác nhận đã đăng theo từng sàn.
5. Đóng/mở ứng dụng không làm mất dữ liệu JSON cũ. Token không được lưu trong manifest hoặc log.

## Phạm vi chưa hoàn tất

- Chưa có icon artwork riêng, wizard onboarding, hệ thống thông báo custom toast và chuyển sáng/tối tùy chỉnh.
- Chưa có đo tốc độ thao tác hay screenshot kiểm chứng giao diện ở thiết bị người dùng.
- Cần kiểm tra thêm hoạt động thật trên Windows, đặc biệt khi dùng font và DPI khác.
