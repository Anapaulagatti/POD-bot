# PODBot Free API Radar: thử trước khi mua (01/11/2026)

Mục tiêu: tận dụng những nguồn API **có công bố free tier/credit**, không nhúng API key lạ, proxy không rõ chủ sở hữu, hoặc máy chủ GPU cục bộ. Bộ công cụ mới dùng thư viện Python sẵn có và không tăng trọng lượng EXE với PyTorch/ComfyUI.

## Nguồn đáng dùng, và hiểu đúng chữ “miễn phí”

| Repo / provider | GitHub stars kiểm tra 01/11/2026 | API miễn phí thực tế | Sử dụng trong PODBot |
| --- | ---: | --- | --- |
| [pollinations/pollinations](https://github.com/pollinations/pollinations) | 5.262 | Có Quest Pollen dùng cho một số model; có thể tiêu credit. Yêu cầu secret key `sk_` riêng. Không còn API vô hạn/no-key. | **Tích hợp thử nghiệm**: catalog chính thức + adapter ảnh, chỉ được dùng sau khi xác minh key, chọn model và đồng ý gửi một lượt |
| [BerriAI/litellm](https://github.com/BerriAI/litellm) | 62.484 | Router là phần mềm tự chạy, không cấp quota GPU. | Chưa nhúng vì nặng và yêu cầu thêm service |
| [open-webui/open-webui](https://github.com/open-webui/open-webui) | 157.453 | GUI, không cấp quota miễn phí | Không nhúng |
| [Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI) | 144.432 | Tự chạy workflow, thường cần GPU/model | Không nhúng cho máy yếu |
| [Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/platform/pricing/) | N/A | 10.000 Neurons/ngày ở Workers Free; model không phải model nào cũng free | **Đã có adapter**, ưu tiên thử đầu tiên |
| [Hugging Face Inference Providers](https://huggingface.co/docs/inference-providers/pricing) | N/A | Free user khoảng 0,10 USD credit/tháng, chính sách có thể đổi | Đã có adapter, token riêng; quota giới hạn |

Số sao chỉ giúp đánh giá mức độ phổ biến, **không** bảo đảm an toàn mã nguồn hay giấy phép kết quả in bán. Các thư viện/weight, thiết kế và đầu ra từng model có điều khoản riêng.

## Free API Radar làm được gì?

- Khi mở Cài đặt và bật hộp tự cập nhật (bật sẵn theo yêu cầu), ứng dụng tải **metadata công khai của Pollinations**, tối đa một lần mỗi 6 giờ trong cùng phiên chạy. Nhấn **Làm mới catalog ngay** để chủ động bỏ cache. Không có API key nào gửi ở bước này.
- Danh sách từ endpoint cố định `https://gen.pollinations.ai/image/models?source=official` được giới hạn dung lượng (2 MB), timeout 12 giây, không theo redirect và không chạy mã từ metadata.
- Model chỉ được thêm vào danh sách tạo ảnh sau khi chọn **Pollinations** và bấm **Kiểm tra key + tải model**. Key được kiểm tra bằng lệnh GET read-only tới `/account/key`; không tạo ảnh. Chỉ model với `paid_only: false` **và** metadata hỗ trợ tạo ảnh mới có thể chọn. Nếu schema metadata thay đổi/thiếu thì fail closed, không đoán.
- Nhãn **Quest-eligible** chỉ có nghĩa có thể dùng Quest Pollen. Nó **không** có nghĩa giá bằng 0; account có thể tiêu credit. Model `paid_only` và model thiếu metadata được loại khỏi danh sách có thể thử.
- Tạo ảnh dùng một POST chính thức `/v1/images/generations`, một ảnh mỗi lần; mỗi yêu cầu đều đòi xác nhận nguy cơ tính phí và đặt chỗ trong giới hạn lượt/ngày. Không tự retry, không chuyển sang model đắt hơn, không tải từ URL trả về lạ.
- Key nằm trong header Authorization; không đặt trong URL/manifest. Có thể chủ động lưu trong Windows Credential Manager nếu người dùng đồng ý.
- Không có tự động `git pull`, cài packages, chạy script bên thứ ba, hoặc chọn model vừa được cập nhật để phát sinh chi phí. **Tự cập nhật danh mục, không tự đổi code của ứng dụng.**

## Quy trình thử an toàn

1. Mở Cloudflare Workers AI Free để thử quota được công bố hằng ngày, xem điều khoản model FLUX và ghi số lượt trên dashboard.
2. Nếu muốn đa dạng model hơn, tạo tài khoản Pollinations ở https://enter.pollinations.ai. Tạo secret `sk_` của riêng bạn, giới hạn quyền chỉ những model ảnh cần thiết và đặt hạn mức ngân sách thật thấp ở dashboard. Nếu chỉ muốn dùng credit miễn phí, **không nạp Paid Pollen**. Tình trạng Quest Pollen được xem trực tiếp trên tài khoản.
3. Trong PODBot, nhập `POLLINATIONS_API_KEY`, chọn Pollinations và kiểm tra key/danh mục bằng GET. Chọn model Quest-eligible, giữ **SEO offline**, chạy một ảnh prompt đơn giản sau khi xác nhận có thể mất credit.
4. So sánh ảnh gốc và bản tách chroma trên áo đen/trắng/navy, độ nét/OCR/alpha và điều khoản thương mại. Không chấp thuận thương mại tự động.

## Giới hạn kiểm chứng

- Chỉ có unit test với HTTP giả lập, chưa sử dụng key thật hay trừ Pollen để kiểm thử ảnh Pollinations. Schema/giá/model có thể thay đổi bất kỳ lúc nào. Danh mục mới từ máy chủ **không chứng minh** key có đủ quota hoặc provider tạo ảnh được.
- Mức miễn phí Cloudflare và Hugging Face được trích từ tài liệu chính thức vào 01/11/2026; cần kiểm lại khi dùng. Không có cách nào đảm bảo dùng miễn phí mãi mãi.
- Model có trong danh mục hoặc repo mã MIT không bảo đảm quyền sử dụng ảnh thương mại; hãy kiểm tra license của model và điều khoản đầu ra.
