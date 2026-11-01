# PODBot Studio · 1.0 Preview 3 (Giao diện tiếng Việt)

**Ứng dụng Windows local cho Print-on-Demand.** Tạo ảnh AI, chọn nhà cung cấp, nhập PNG/JPEG/WebP riêng không mất phí ảnh, chuẩn hóa PNG, duyệt QC, chỉnh SEO và hỗ trợ đăng Redbubble/TeePublic theo quy trình **do người dùng xác nhận**.

Phiên bản kỹ thuật `1.0.0rc3` (1.0 Preview 3). Đây là bản thử nghiệm, không phải bản sản xuất đã ký mã. Các bản 4.x trước đây chỉ mang ý nghĩa tên bản thử nghiệm và được giữ trong CHANGELOG để tra cứu.

## Free API Radar: tìm model thử trước khi mua

- **Cloudflare Workers AI Free** là lựa chọn đầu tiên vì có hạn mức miễn phí được nhà cung cấp công bố. Adapter Cloudflare đã có sẵn.
- **Pollinations**: API catalog public tự làm mới **chỉ sau khi người dùng bật tùy chọn (mặc định TẮT)**, khi mở **Cài đặt** (cache 6 giờ); không gửi key, không tạo ảnh. Nếu muốn thử, dùng **POLLINATIONS_API_KEY** riêng (`sk_`), chọn Pollinations → Kiểm tra key + tải model, chỉ model hỗ trợ Quest Pollen và endpoint ảnh tương thích mới được đưa vào danh sách.
- **Lưu ý quan trọng:** Quest Pollen là credit có thể bị trừ, không phải giá $0. Mỗi lần thử đều cần xác nhận và bị giới hạn số request/ngày; key phải có hạn mức ngân sách trên dashboard nhà cung cấp. Không tự cài plugin, không tự chạy model mới, không dùng key chia sẻ.
- [Xem bảng repo uy tín, điều kiện miễn phí và hướng dẫn test](docs/FREE_API_RADAR.md).

## ProMax Lite: nâng cấp cho máy cấu hình yếu

- **Prompt có cấu trúc, 0 phí dựng prompt:** Trang **Sáng tạo AI → Bộ dựng prompt có cấu trúc**. Chọn chủ thể, phong cách, bố cục, 1–6 màu HEX, nền chroma xanh/hồng, trắng phẳng hoặc trong suốt (nếu model hỗ trợ) và quy tắc chữ. Bấm **Dựng prompt** để tự soạn lời nhắc trên máy, không có request API. Chỉ khi bạn bấm **Tạo bằng AI** và xác nhận phí thì mới gửi đi.
- **Truy vết prompt:** Manifest lưu phiên bản bộ dựng, công thức và SHA256 của lời nhắc thực gửi; nếu chỉnh prompt thủ công, ứng dụng không giả vờ giữ nguồn gốc bộ dựng.
- **Chroma key + cắt nền tự động:** Mặc định với model chưa xác minh alpha là nền hồng sen phẳng; ảnh gốc được giữ nguyên, Pillow thử tách nền và cảnh báo nếu không an toàn. Không cần GPU.\n- **QC tiết kiệm RAM:** Thu nhỏ trước khi đổi sang RGBA ở các phép thống kê; chưa cam kết mức RAM đỉnh cụ thể trên máy thật.\n- **Vector hóa VTracer tùy chọn:** Thư viện → **Xuất SVG (VTracer)**, tự chọn `vtracer.exe` đã cài từ nguồn tin cậy. Dùng PNG in đã tách nền, chạy CPU, giới hạn đầu vào 1600 px, tối đa 6 màu, 180 giây, kiểm tra SVG đầu ra. **Không tự thay đổi file PNG, duyệt bán hoặc tự cài thêm model.**
- **EXE chuẩn gọn nhẹ:** Không tích hợp CUDA, PyTorch, BiRefNet, LayerDiffuse, ComfyUI, Spandrel, CLIP hay model 7B. Tách nền Pillow và xem trước trên màu áo vẫn có sẵn; rembg là tùy chọn riêng.

Xem [hướng dẫn ProMax Lite](docs/PROMAX_LITE.md) và [skill CPU-first](.claude/skills/promax-cpu-lite/SKILL.md) để biết chính xác các giới hạn và cách dùng.

## Bắt đầu trong Windows

1. Trên [GitHub Actions](https://github.com/Anapaulagatti/POD-bot/actions), chọn workflow thành công của nhánh `main`; tải `PODBot-windows-onedir`, giải nén và chạy `PODBot/PODBot.exe`. Bản một-file được tạo khi chạy workflow thủ công hoặc phát hành bằng tag.
2. Mở **Cài đặt API** nếu muốn tạo ảnh AI bằng Cloudflare, Hugging Face, Gemini, OpenAI, Replicate, fal.ai hoặc Stability AI. API key chỉ giữ trong RAM hoặc biến môi trường theo mặc định; có thể chủ động lưu vào kho khóa hệ điều hành.
3. Mở **Sáng tạo AI**, chọn model, prompt và SEO. Với model tính phí, người dùng xác nhận trước; không tự chuyển model và không tự thử lại có phí. Hoặc chọn **Nhập ảnh từ máy**, không dùng API ảnh.
4. Vào **Thư viện thiết kế**, kiểm tra file PNG, sửa SEO, tạo mockup và kiểm tra chất lượng in. Duyệt thương mại sau khi QC đạt và xác nhận quyền sử dụng.
5. Mở trang sàn để tự đăng sản phẩm, sau đó bấm **Đã đăng** nếu thực sự đã kiểm tra trên tài khoản bán.

## Kiểm tra mới và hàng đợi offline

- Mở **Thư viện thiết kế → Hàng đợi** để xem, thử lại (nếu còn lượt) hoặc hủy tác vụ đang chờ. Khôi phục tác vụ offline bị ngắt sau khi khởi động lại; tác vụ có phí vẫn cần xác nhận riêng và không tự phát lại.
- **Kiểm tra ảnh** quét chữ trên nền trắng và đen (khi PNG có alpha). OCR được nối vào bước duyệt bán: từ/cụm từ khớp blocklist làm **FAIL**, chữ xuất hiện khi prompt ghi `no text` tạo **WARN**. Nếu OCR chưa cài, ứng dụng cảnh báo và bạn phải tự rà soát chữ, không được hiểu là đã kiểm chứng.
- Cài Tesseract riêng và đặt `PODBOT_TESSERACT_PATH` nếu không có trong PATH. Không tải model OCR tự động.
- **Khám phá xu hướng** cho xem chủ đề, từ khóa gợi ý từ Google Trends RSS và tiêu đề tin liên quan; có thể sao chép hoặc dùng để điền form tạo thiết kế sau khi xác nhận. Các từ khóa này KHÔNG phải Google Related Queries được đo riêng.
- Khi xử lý lại một thiết kế từng được duyệt/đăng, giao diện cảnh báo rằng trạng thái sàn sẽ trở về `draft`.
- [Nguồn GitHub/skill đề xuất để nâng cấp](docs/UPGRADE_REPOS_AND_QA.md).
- Tham khảo [hướng dẫn chất lượng và hàng đợi](docs/QUALITY_AND_OFFLINE_JOBS.md).

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

## Có gì mới trong Preview 3: tách nền không cần ML

**Xóa nền phẳng ngay trong EXE tiêu chuẩn:** Thư viện → chọn thiết kế → **Xử lý lại ảnh** → chọn **Có** ở hộp thoại "Tách nền phẳng bằng Pillow". Thuật toán tìm màu nền tương đối đồng nhất ở bốn góc và flood-fill các vùng màu tương tự nối với mép, sau đó làm mềm alpha. Chạy offline, không dùng API hoặc weights ML. Nếu bốn góc khác nhau, nền chuyển sắc, hoặc nghi ngờ xóa quá nhiều, ứng dụng từ chối. **Đây không phải bộ nhận diện chủ thể bằng AI**; cần xem kỹ màu áo và chữ/nét trắng sau khi xử lý.

**Prompt dễ xóa nền:** Trang Sáng tạo AI có ô **Thêm gợi ý nền trắng phẳng** bật mặc định, có thể tắt. Nội dung gốc vẫn được lưu; manifest ghi thêm `prompt_sent` và `flat_background_prompt`. Prompt có thể không được model làm theo, nên đây chỉ là trợ giúp, không đảm bảo ảnh trong suốt.

**Di chuyển hash cũ (v1 → v2):**

```powershell
podbot rehash --dry-run
podbot rehash
# Xử lý nền phẳng từ CLI, không gọi mô hình AI:
podbot process --id YOUR_DESIGN_ID --flat-bg
# Chỉ thêm gợi ý nền phẳng khi tạo từ CLI:
podbot create --provider cloudflare --flat-prompt --niche "flowers" --prompt "Original floral artwork" --keywords "flowers,nature"
```

Rehash đọc file `source.png` bên trong mỗi thư mục thiết kế và ghi lại fingerprint v2 theo kiểu atomic. **Không sửa ảnh, SEO, trạng thái duyệt hoặc quyền thương mại.** Manifest thiếu ảnh nguồn được đếm vào báo cáo lỗi và bỏ qua. Nên sao lưu thư mục dữ liệu trước khi chạy với thư viện lớn.

**Hiệu năng rembg:** Tái sử dụng session đã nạp bằng `lru_cache(maxsize=3)` trong cùng một phiên Python. RemBg vẫn là tùy chọn riêng (ML runtime không nằm trong EXE tiêu chuẩn).

**Hạn mức API:** đếm theo ngày địa phương của máy Windows; reset vào 00:00 theo giờ hệ điều hành. Nếu có `PODBOT_PAID_CALLS_PER_DAY`, ứng dụng hiển thị cảnh báo nó đang ghi đè con số trong Settings. Giới hạn vẫn là số lượt gọi, không phải tiền.

**Đóng gói và phát hành:** Đã thêm workflow khi push tag `v*` để dựng `--onedir` + bản `--onefile`, kiểm tra `pip-audit`, và đăng SHA256SUMS + bản snapshot phiên bản thư viện đã giải quyết trong Release. Xem [Quy trình Release](docs/WINDOWS_RELEASE.md). Workflow chỉ tạo bản phát hành khi một tag phù hợp đã được push và job thành công. Một bản build CI xanh không có nghĩa đã ký mã, không có virus hay thử trên mọi Windows.

**Chưa làm:** OCR, hàng đợi công việc bền vững có hủy/retry, chia UI thành các trang riêng, installer, chữ ký số, khóa phụ thuộc đầy đủ có hash đã commit và thử API bằng key trả phí thực.
