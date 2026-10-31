# ECC cho dự án POD-bot trên Windows

Đã đặt **project-scoped Claude Code skills** vào `.claude/skills/` và quy tắc vào `.claude/rules/`. Các nội dung này lấy từ https://github.com/affaan-m/ECC (MIT, bản gốc Affaan Mustafa); xem [ECC_INTEGRATION.md](ECC_INTEGRATION.md) và [ECC_LICENSE.txt](ECC_LICENSE.txt).

Bạn chỉ cần mở thư mục dự án trong Claude Code nếu muốn dùng bộ skill project-local. Đây **không phải** bộ cài toàn bộ ECC, không tự cài các hook/agents bên ngoài, không ảnh hưởng đến PODBot.exe.

**Nếu muốn dùng toàn bộ ECC native plugin trên Claude Code Windows**, hãy chuyển sang cách cài chính thức và tránh giữ đồng thời các skill trùng lặp:

1. Cài Node.js >=18, Git và Claude Code >=2.1.
2. Trong Claude Code, nhập:

```text
/plugin marketplace add https://github.com/affaan-m/ECC
/plugin install ecc@ecc
```

3. Xác minh `/plugin list`.

Cách thay thế: mở PowerShell, chạy `npx ecc-universal@2.2.3 setup` theo hướng dẫn gốc. **Chọn đúng một phương thức**, không chạy lệnh không rõ nguồn. Chưa có thao tác nào trên máy Windows cá nhân của bạn được thực hiện từ ChatGPT.
