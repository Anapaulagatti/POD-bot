"""Vietnamese desktop design tokens and static labels, independent of Tk."""

BG = "#0B1220"
SIDEBAR = "#101B2B"
CARD = "#152438"
CARD_ALT = "#1D3047"
BORDER = "#263C54"
ACCENT = "#30DBC2"
ACCENT_HOVER = "#1DBEA8"
ACCENT_TEXT = "#082923"
WHITE = "#F1F7FC"
MUTED = "#9DB0C2"
DANGER = "#FB7185"
WARNING = "#F5BD67"
N_FONT = "Segoe UI"

PLATFORMS = {"redbubble": "Redbubble", "teepublic": "TeePublic"}
UPLOADER = {
    "redbubble": "https://www.redbubble.com/portfolio/images/new",
    "teepublic": "https://www.teepublic.com/",
}

MENU = (
    ("overview", "⌂  Tổng quan"),
    ("create", "✦  Sáng tạo AI"),
    ("library", "▦  Thư viện thiết kế"),
    ("trends", "◈  Xu hướng"),
    ("settings", "⚙  Cài đặt API"),
)

TEXT = {
    "app": "PODBot Studio",
    "language": "Tiếng Việt",
    "ready": "Sẵn sàng. Các thiết kế phải được duyệt trước khi đăng bán.",
    "create": "Tạo thiết kế",
    "import": "Nhập ảnh từ máy (không tốn phí AI)",
    "rights": "Tôi xác nhận có quyền thương mại với hình ảnh và nội dung sản phẩm.",
    "paid": "Lệnh tạo ảnh hoặc SEO này có thể bị tính phí API. Tiếp tục?",
    "status_draft": "Bản nháp",
    "status_approved": "Đã duyệt",
    "status_uploaded": "Đã đăng",
    "empty": "Chưa có thiết kế. Hãy tạo bằng AI hoặc nhập ảnh từ máy.",
    "no_selection": "Vui lòng chọn một thiết kế trong thư viện.",
}
STATUSES = {
    "draft": TEXT["status_draft"],
    "approved": TEXT["status_approved"],
    "uploaded": TEXT["status_uploaded"],
}

