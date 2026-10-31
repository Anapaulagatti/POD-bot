"""PODBot Studio: modern Vietnamese-first CustomTkinter desktop shell.

Existing providers, image processing, quality gates, and publishing stay in independent
modules. No network calls on the UI thread. Never store API keys or auto-post to stores.
"""

from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from podbot.audit import audit_image, find_blocked_terms, get_blocklist, make_color_preview
from podbot.importer import import_design
from podbot.mockups import create_shirt_mockup
from podbot.pipeline import create_draft
from podbot.processing import ProcessOptions, process_stored_design
from podbot.provider_catalog import CATALOG, LABELS, get_spec, make_provider
from podbot.publishing import POLICY_URLS, approve_listing, confirm_rights, mark_uploaded
from podbot.settings import data_directory
from podbot.storage import export_csv, list_designs, update_seo
from podbot.trends import read_trends

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

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


def model_options() -> list[str]:
    return [spec.label for spec in CATALOG]


def status_label(state: str) -> str:
    return STATUSES.get(state, state)


class PODBotDesktop(ctk.CTk):
    """Single-window, five-page navigation and event-driven background work."""

    def __init__(self) -> None:
        super().__init__()
        self.title("PODBot Studio · Giao diện tiếng Việt")
        self.geometry("1240x790")
        self.minsize(940, 660)
        self.configure(fg_color=BG)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.busy = False
        self.records: dict[str, dict] = {}
        self.selected_id: str | None = None
        self.preview_image: ctk.CTkImage | None = None
        self.current_page = "overview"
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        self.pages: dict[str, ctk.CTkScrollableFrame] = {}

        self.model = tk.StringVar(value=CATALOG[0].label)
        self.seo = tk.StringVar(value="SEO offline (miễn phí)")
        self.resolution = tk.StringVar(value="2K")
        self.niche = tk.StringVar(value="minh họa thiên nhiên")
        self.keywords = tk.StringVar(value="mountain, nature, hiking")
        self.platform = tk.StringVar(value="redbubble")
        self.country = tk.StringVar(value="US")
        self.keys = {
            field: tk.StringVar(value=os.getenv(field, ""))
            for field in (
                "CLOUDFLARE_ACCOUNT_ID",
                "CLOUDFLARE_API_TOKEN",
                "HF_TOKEN",
                "GEMINI_API_KEY",
                "OPENAI_API_KEY",
                "REPLICATE_API_TOKEN",
                "FAL_KEY",
                "STABILITY_API_KEY",
            )
        }
        self.message = tk.StringVar(value=TEXT["ready"])
        self._layout()
        self.refresh()
        self.show_page("overview")
        self.after(120, self._handle_events)

    @staticmethod
    def _font(size: int, *, bold: bool = False) -> ctk.CTkFont:
        return ctk.CTkFont(family=N_FONT, size=size, weight="bold" if bold else "normal")

    def _label(self, parent, text: str, size: int = 13, *,
               fg: str = WHITE, bold: bool = False, **kwargs):
        return ctk.CTkLabel(
            parent, text=text, text_color=fg, font=self._font(size, bold=bold),
            anchor="w", **kwargs,
        )

    def _button(self, parent, text: str, command, *, primary: bool = False,
                width: int = 120):
        return ctk.CTkButton(
            parent, text=text, command=command, width=width, height=38,
            corner_radius=11, font=self._font(12, bold=True),
            fg_color=ACCENT if primary else CARD_ALT,
            hover_color=ACCENT_HOVER if primary else BORDER,
            text_color=ACCENT_TEXT if primary else WHITE,
        )

    def _card(self, parent, *, padding: int = 18) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=16,
                             border_width=1, border_color=BORDER)
        return frame

    def _layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        sidebar = ctk.CTkFrame(self, width=228, fg_color=SIDEBAR, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=22, pady=(28, 29))
        self._label(brand, "✦  PODBot", 25, bold=True).pack(anchor="w")
        self._label(brand, "STUDIO  4.1  •  VI", 11, fg=ACCENT, bold=True).pack(
            anchor="w", pady=(3, 0),
        )

        self._label(sidebar, "KHÔNG GIAN LÀM VIỆC", 10, fg=MUTED, bold=True).pack(
            anchor="w", padx=22, pady=(0, 12),
        )
        for key, title in MENU:
            button = ctk.CTkButton(
                sidebar, text=title, anchor="w", height=48, corner_radius=12,
                fg_color="transparent", hover_color=CARD_ALT,
                text_color=MUTED, font=self._font(13, bold=True),
                command=lambda page=key: self.show_page(page),
            )
            button.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[key] = button

        ctk.CTkFrame(sidebar, fg_color="transparent").pack(fill="both", expand=True)
        self._label(sidebar, "CHẾ ĐỘ ĐĂNG BÁN", 10, fg=MUTED, bold=True).pack(
            anchor="w", padx=22,
        )
        self._label(sidebar, "●  Có xác nhận của bạn", 12, fg=ACCENT).pack(
            anchor="w", padx=22, pady=(7, 4),
        )
        self._label(sidebar, "Không tự động đăng hàng loạt", 11, fg=MUTED).pack(
            anchor="w", padx=22, pady=(0, 24),
        )

        right = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(right, height=70, fg_color=BG, corner_radius=0)
        top.grid(row=0, column=0, sticky="ew", padx=27)
        self.page_title = self._label(top, "Tổng quan", 19, bold=True)
        self.page_title.pack(side="left", pady=(20, 9))
        self._label(top, "TIẾNG VIỆT  •  WINDOWS LOCAL", 10, fg=MUTED).pack(
            side="right", pady=(21, 9),
        )
        self.workspace = ctk.CTkFrame(right, fg_color=BG, corner_radius=0)
        self.workspace.grid(row=1, column=0, sticky="nsew")
        footer = ctk.CTkFrame(right, height=44, fg_color=SIDEBAR, corner_radius=0)
        footer.grid(row=2, column=0, sticky="ew")
        self._label(footer, "●  TRẠNG THÁI", 10, fg=ACCENT, bold=True).pack(
            side="left", padx=(25, 14),
        )
        self._label(footer, "", 11, fg=MUTED, textvariable=self.message).pack(
            side="left", fill="x", expand=True,
        )
        for key in ("overview", "create", "library", "trends", "settings"):
            self.pages[key] = ctk.CTkScrollableFrame(
                self.workspace, fg_color="transparent", corner_radius=0,
                scrollbar_button_color=BORDER,
            )
        self._overview()
        self._create()
        self._library()
        self._trends()
        self._settings()

    def show_page(self, key: str) -> None:
        titles = {
            "overview": "Tổng quan", "create": "Sáng tạo bằng AI",
            "library": "Thư viện & đăng bán", "trends": "Khám phá xu hướng",
            "settings": "Cài đặt API",
        }
        for page in self.pages.values():
            page.pack_forget()
        self.pages[key].pack(fill="both", expand=True, padx=18, pady=(0, 8))
        self.current_page = key
        self.page_title.configure(text=titles[key])
        for page_key, button in self.nav_buttons.items():
            active = key == page_key
            button.configure(
                fg_color=CARD_ALT if active else "transparent",
                text_color=ACCENT if active else MUTED,
            )
        if key in {"library", "overview"}:
            self.refresh()

    def _section(self, parent, title: str, description: str) -> None:
        self._label(parent, title, 27, bold=True).pack(anchor="w", padx=9, pady=(13, 4))
        self._label(parent, description, 12, fg=MUTED, wraplength=750).pack(
            anchor="w", padx=9, pady=(0, 20),
        )

    def _overview(self) -> None:
        page = self.pages["overview"]
        hero = ctk.CTkFrame(page, fg_color="#123C44", corner_radius=20)
        hero.pack(fill="x", padx=8, pady=(12, 16))
        self._label(hero, "PODBOT  /  CREATIVE DESKTOP", 11, fg=ACCENT, bold=True).pack(
            anchor="w", padx=26, pady=(24, 9),
        )
        self._label(hero, "Biến ý tưởng thành thiết kế POD.", 27, bold=True).pack(
            anchor="w", padx=26,
        )
        self._label(
            hero, "Tạo ảnh AI, tối ưu SEO, kiểm tra chất lượng và chuẩn bị đăng bán "
            "trên Redbubble hoặc TeePublic, tất cả trong một ứng dụng.",
            13, fg="#C2E1E1", wraplength=700,
        ).pack(anchor="w", padx=26, pady=(9, 20))
        self._button(hero, "✦  Tạo thiết kế mới", lambda: self.show_page("create"),
                     primary=True, width=194).pack(anchor="w", padx=26, pady=(0, 24))

        self.stats = ctk.CTkFrame(page, fg_color="transparent")
        self.stats.pack(fill="x", padx=7, pady=(0, 15))
        for col in range(3):
            self.stats.grid_columnconfigure(col, weight=1)
        self.stat_labels: dict[str, ctk.CTkLabel] = {}
        for col, (key, caption) in enumerate((
            ("total", "THIẾT KẾ ĐÃ LƯU"),
            ("approved", "ĐƯỢC PHÊ DUYỆT"),
            ("uploaded", "ĐÃ ĐĂNG BÁN"),
        )):
            card = self._card(self.stats)
            card.grid(row=0, column=col, sticky="ew", padx=5)
            self._label(card, caption, 10, fg=MUTED, bold=True).pack(
                anchor="w", padx=18, pady=(16, 8),
            )
            value = self._label(card, "0", 31, bold=True)
            value.pack(anchor="w", padx=18, pady=(0, 16))
            self.stat_labels[key] = value

        recent = self._card(page)
        recent.pack(fill="x", padx=8, pady=(0, 12))
        self._label(recent, "Thiết kế gần đây", 17, bold=True).pack(
            anchor="w", padx=20, pady=(19, 5),
        )
        self.recent_text = self._label(
            recent, "Chưa có dữ liệu thiết kế.", 13, fg=MUTED, wraplength=770,
            justify="left",
        )
        self.recent_text.pack(anchor="w", padx=20, pady=(0, 22))
        quick = self._card(page)
        quick.pack(fill="x", padx=8, pady=(0, 18))
        self._label(quick, "Quy trình bảo vệ thiết kế", 16, bold=True).pack(
            anchor="w", padx=20, pady=(18, 9),
        )
        self._label(
            quick,
            "① Tạo ảnh hoặc nhập PNG   →   ② Kiểm tra chất lượng và SEO\n"
            "③ Xác nhận quyền thương mại   →   ④ Duyệt từng sàn   →   ⑤ Đăng thủ công",
            13, fg=MUTED, justify="left",
        ).pack(anchor="w", padx=20, pady=(0, 20))

    def _create(self) -> None:
        page = self.pages["create"]
        self._section(
            page, "Studio sáng tạo",
            "Mỗi lần bấm tạo sẽ gửi một yêu cầu đến model đã chọn. "
            "Hãy kiểm tra chi phí của nhà cung cấp trước khi sử dụng.",
        )
        form = self._card(page)
        form.pack(fill="x", padx=8, pady=(0, 16))
        self._label(form, "MÔ TẢ THIẾT KẾ / PROMPT", 11, fg=ACCENT, bold=True).pack(
            anchor="w", padx=20, pady=(19, 8),
        )
        self.prompt_box = ctk.CTkTextbox(
            form, height=115, font=self._font(13), corner_radius=10,
            fg_color=BG, text_color=WHITE, border_width=1, border_color=BORDER,
            wrap="word",
        )
        self.prompt_box.pack(fill="x", padx=20)
        self.prompt_box.insert(
            "1.0", "Original minimalist mountain sunrise illustration, crisp shapes, "
            "centered composition for T-shirt print, no lettering, no logos, transparent background",
        )
        fields = ctk.CTkFrame(form, fg_color="transparent")
        fields.pack(fill="x", padx=20, pady=(14, 6))
        fields.grid_columnconfigure((0, 1), weight=1)
        for col, (label, variable) in enumerate((
            ("CHỦ ĐỀ / NGÁCH BÁN", self.niche),
            ("TỪ KHÓA (CÁCH NHAU BẰNG DẤU PHẨY)", self.keywords),
        )):
            group = ctk.CTkFrame(fields, fg_color="transparent")
            group.grid(row=0, column=col, sticky="ew", padx=(0, 9) if col == 0 else (9, 0))
            self._label(group, label, 10, fg=MUTED, bold=True).pack(
                anchor="w", pady=(0, 7),
            )
            ctk.CTkEntry(
                group, textvariable=variable, height=41, corner_radius=10,
                fg_color=BG, border_color=BORDER, text_color=WHITE,
                font=self._font(12),
            ).pack(fill="x")
        self._label(form, "MÔ HÌNH TẠO ẢNH", 10, fg=MUTED, bold=True).pack(
            anchor="w", padx=20, pady=(15, 7),
        )
        self.model_dropdown = ctk.CTkOptionMenu(
            form, values=model_options(), variable=self.model,
            height=42, corner_radius=10, fg_color=CARD_ALT,
            button_color="#284C64", button_hover_color=BORDER,
            text_color=WHITE, font=self._font(12),
            command=self._model_changed,
        )
        self.model_dropdown.pack(fill="x", padx=20)

        options = ctk.CTkFrame(form, fg_color="transparent")
        options.pack(fill="x", padx=20, pady=(14, 4))
        options.grid_columnconfigure((0, 1), weight=1)
        seo_group = ctk.CTkFrame(options, fg_color="transparent")
        seo_group.grid(row=0, column=0, sticky="ew", padx=(0, 9))
        self._label(seo_group, "SEO", 10, fg=MUTED, bold=True).pack(anchor="w", pady=(0, 6))
        ctk.CTkOptionMenu(
            seo_group, values=["SEO offline (miễn phí)", "Gemini AI SEO (có thể tính phí)"],
            variable=self.seo, height=40, corner_radius=10, fg_color=CARD_ALT,
            button_color="#284C64", text_color=WHITE,
        ).pack(fill="x")
        size_group = ctk.CTkFrame(options, fg_color="transparent")
        size_group.grid(row=0, column=1, sticky="ew", padx=(9, 0))
        self._label(size_group, "ĐỘ PHÂN GIẢI GEMINI", 10, fg=MUTED, bold=True).pack(
            anchor="w", pady=(0, 6),
        )
        ctk.CTkOptionMenu(
            size_group, values=["1K", "2K", "4K"], variable=self.resolution,
            height=40, corner_radius=10, fg_color=CARD_ALT,
            button_color="#284C64", text_color=WHITE,
        ).pack(fill="x")
        self.model_explanation = self._label(
            form, "", 11, fg=MUTED, wraplength=680, justify="left",
        )
        self.model_explanation.pack(anchor="w", padx=20, pady=(12, 11))
        buttons = ctk.CTkFrame(form, fg_color="transparent")
        buttons.pack(fill="x", padx=20, pady=(0, 20))
        self.create_button = self._button(
            buttons, "✦  Tạo bằng AI", self.generate, primary=True, width=165,
        )
        self.create_button.pack(side="left", padx=(0, 10))
        self._button(
            buttons, "↑  Nhập ảnh từ máy (0 phí API)",
            self.import_file, width=230,
        ).pack(side="left")
        self._model_changed(self.model.get())

        note = self._card(page)
        note.pack(fill="x", padx=8, pady=(0, 18))
        self._label(note, "Lưu ý trước khi tạo", 14, bold=True).pack(
            anchor="w", padx=18, pady=(17, 7),
        )
        self._label(
            note, "Không dùng hình nhân vật bản quyền hoặc nhãn hiệu khi chưa được phép. "
            "Ảnh AI chưa chắc có nền trong suốt hoặc đủ chi tiết để in. "
            "Bộ kiểm tra chất lượng sẽ hỗ trợ bạn trước khi đăng bán.",
            12, fg=MUTED, wraplength=740, justify="left",
        ).pack(anchor="w", padx=18, pady=(0, 19))

    def _model_changed(self, _value: str) -> None:
        model_id = LABELS.get(self.model.get())
        if model_id:
            spec = get_spec(model_id)
            pricing = "Dịch vụ tính phí" if spec.paid else "Hạn mức / tín dụng có giới hạn"
            self.model_explanation.configure(
                text=f"ℹ  {pricing}  •  {spec.hint}  •  API key: {spec.env_key}",
            )

    def _library(self) -> None:
        page = self.pages["library"]
        self._section(
            page, "Thư viện thiết kế",
            "Quản lý file PNG, chỉnh SEO, xử lý ảnh và duyệt đăng bán theo từng nền tảng.",
        )
        control = self._card(page)
        control.pack(fill="x", padx=8, pady=(0, 12))
        row = ctk.CTkFrame(control, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=13)
        self._button(row, "↻  Làm mới", self.refresh, width=116).pack(side="left")
        self._label(row, "NỀN TẢNG", 10, fg=MUTED, bold=True).pack(
            side="left", padx=(20, 10),
        )
        ctk.CTkOptionMenu(
            row, values=list(PLATFORMS), variable=self.platform, width=146,
            fg_color=CARD_ALT, button_color="#284C64", text_color=WHITE,
            command=lambda _value: self._update_inspector(),
        ).pack(side="left")

        selector = self._card(page)
        selector.pack(fill="x", padx=8, pady=(0, 12))
        self._label(selector, "Chọn thiết kế", 15, bold=True).pack(
            anchor="w", padx=18, pady=(15, 7),
        )
        self.library_list = ctk.CTkScrollableFrame(
            selector, height=185, fg_color="transparent",
        )
        self.library_list.pack(fill="x", padx=10, pady=(0, 12))
        detail = self._card(page)
        detail.pack(fill="x", padx=8, pady=(0, 16))
        self._label(detail, "Chi tiết sản phẩm và thao tác", 16, bold=True).pack(
            anchor="w", padx=20, pady=(18, 9),
        )
        info = ctk.CTkFrame(detail, fg_color="transparent")
        info.pack(fill="x", padx=20, pady=(0, 12))
        self.art_preview = self._label(info, "CHƯA CHỌN ẢNH", 13, fg=MUTED)
        self.art_preview.pack(side="left", padx=(0, 17), pady=9)
        text_area = ctk.CTkFrame(info, fg_color="transparent")
        text_area.pack(side="left", fill="x", expand=True)
        self.detail_name = self._label(
            text_area, "Chọn một thiết kế ở phía trên", 14, bold=True, wraplength=430,
        )
        self.detail_name.pack(anchor="w")
        self.detail_status = self._label(text_area, "", 12, fg=ACCENT)
        self.detail_status.pack(anchor="w", pady=(7, 0))
        self.detail_warning = self._label(
            text_area, "", 11, fg=WARNING, wraplength=440, justify="left",
        )
        self.detail_warning.pack(anchor="w", pady=(8, 0))
        self._label(detail, "THAO TÁC THIẾT KẾ", 10, fg=MUTED, bold=True).pack(
            anchor="w", padx=20, pady=(6, 9),
        )
        edits = ctk.CTkFrame(detail, fg_color="transparent")
        edits.pack(fill="x", padx=20)
        for title, cmd in (
            ("Xem PNG", self.open_png),
            ("Chỉnh SEO", self.edit_seo),
            ("Kiểm tra chất lượng", self.preflight),
            ("Xử lý lại ảnh", self.process_image),
            ("Xem màu áo", self.preview_colors),
        ):
            self._button(edits, title, cmd, width=131).pack(side="left", padx=(0, 7), pady=(0, 10))
        self._label(detail, "DUYỆT VÀ ĐĂNG SẢN PHẨM", 10, fg=MUTED, bold=True).pack(
            anchor="w", padx=20, pady=(13, 9),
        )
        publish = ctk.CTkFrame(detail, fg_color="transparent")
        publish.pack(fill="x", padx=20, pady=(0, 20))
        for title, cmd, primary in (
            ("✓  Duyệt thiết kế", self.approve, True),
            ("↗  Mở trang đăng", self.open_store, False),
            ("Đã đăng", self.mark_uploaded, False),
            ("Xuất CSV đã duyệt", self.export, False),
        ):
            self._button(publish, title, cmd, primary=primary, width=151).pack(
                side="left", padx=(0, 8),
            )

    def _trends(self) -> None:
        page = self.pages["trends"]
        self._section(
            page, "Khám phá xu hướng",
            "Đọc Google Trends RSS trực tiếp. Xu hướng tìm kiếm không đồng nghĩa "
            "với quyền sử dụng thương hiệu hoặc cơ hội bán hàng được đảm bảo.",
        )
        card = self._card(page)
        card.pack(fill="x", padx=8, pady=(0, 12))
        bar = ctk.CTkFrame(card, fg_color="transparent")
        bar.pack(fill="x", padx=18, pady=17)
        self._label(bar, "QUỐC GIA", 11, fg=MUTED, bold=True).pack(side="left", padx=(0, 12))
        ctk.CTkOptionMenu(
            bar, values=["US", "GB", "CA", "AU", "DE", "FR", "JP", "KR", "BR", "IN"],
            variable=self.country, width=110, fg_color=CARD_ALT,
            button_color="#284C64", text_color=WHITE,
        ).pack(side="left")
        self.trend_button = self._button(
            bar, "↻  Tải xu hướng", self.fetch_trends, primary=True, width=160,
        )
        self.trend_button.pack(side="left", padx=13)
        results = self._card(page)
        results.pack(fill="x", padx=8, pady=(0, 16))
        self._label(results, "Chủ đề đang được tìm kiếm", 17, bold=True).pack(
            anchor="w", padx=20, pady=(18, 10),
        )
        self.trend_rows = ctk.CTkScrollableFrame(
            results, height=290, fg_color="transparent",
        )
        self.trend_rows.pack(fill="x", padx=12, pady=(0, 15))
        self._label(
            self.trend_rows, "Bấm “Tải xu hướng” để xem dữ liệu có nguồn.",
            12, fg=MUTED,
        ).pack(anchor="w", padx=12, pady=12)

    def _settings(self) -> None:
        page = self.pages["settings"]
        self._section(
            page, "Cài đặt kết nối AI",
            "Dán API key của dịch vụ bạn sử dụng. Key chỉ được giữ trong bộ nhớ "
            "phiên chạy, không ghi xuống mã nguồn hoặc manifest thiết kế.",
        )
        card = self._card(page)
        card.pack(fill="x", padx=8, pady=(0, 14))
        names = (
            ("CLOUDFLARE_ACCOUNT_ID", "Cloudflare Account ID"),
            ("CLOUDFLARE_API_TOKEN", "Cloudflare API Token"),
            ("HF_TOKEN", "Hugging Face Token"),
            ("GEMINI_API_KEY", "Gemini (tạo ảnh + SEO)"),
            ("OPENAI_API_KEY", "OpenAI API"),
            ("REPLICATE_API_TOKEN", "Replicate"),
            ("FAL_KEY", "fal.ai"),
            ("STABILITY_API_KEY", "Stability AI"),
        )
        for index, (key, label) in enumerate(names):
            self._label(card, label, 12, bold=True).pack(
                anchor="w", padx=20, pady=(19 if index == 0 else 12, 5),
            )
            ctk.CTkEntry(
                card, textvariable=self.keys[key], show="" if "ACCOUNT_ID" in key else "•",
                height=39, corner_radius=10, fg_color=BG, border_color=BORDER,
                text_color=WHITE, placeholder_text=f"Nhập {key} (tùy chọn)",
                font=self._font(12),
            ).pack(fill="x", padx=20, pady=(0, 4))
        self._label(
            card, "Lưu ý: không chia sẻ API key, token hoặc ảnh chụp màn hình chứa thông tin bí mật.",
            11, fg=WARNING, wraplength=730,
        ).pack(anchor="w", padx=20, pady=(14, 20))
        other = self._card(page)
        other.pack(fill="x", padx=8, pady=(0, 17))
        self._label(other, "Tệp và quyền riêng tư", 16, bold=True).pack(
            anchor="w", padx=19, pady=(18, 8),
        )
        self._label(
            other, "Ảnh, bản nháp và SEO lưu trên máy. Bạn kiểm soát "
            "việc duyệt và tải lên Redbubble / TeePublic.",
            12, fg=MUTED, wraplength=710,
        ).pack(anchor="w", padx=19, pady=(0, 12))
        buttons = ctk.CTkFrame(other, fg_color="transparent")
        buttons.pack(anchor="w", padx=18, pady=(0, 20))
        self._button(
            buttons, "Mở thư mục dữ liệu",
            lambda: self._open_file(data_directory()), width=180,
        ).pack(side="left", padx=(0, 9))
        self._button(
            buttons, "Sửa danh sách từ khóa cảnh báo",
            self.edit_blocklist, width=255,
        ).pack(side="left")

    def refresh(self) -> None:
        self.records = {entry["id"]: entry for entry in list_designs()}
        if self.selected_id not in self.records:
            self.selected_id = next(iter(self.records), None)
        total = len(self.records)
        approved = sum(
            1 for entry in self.records.values()
            if "approved" in entry.get("platform_status", {}).values()
        )
        uploaded = sum(
            1 for entry in self.records.values()
            if "uploaded" in entry.get("platform_status", {}).values()
        )
        self.stat_labels["total"].configure(text=str(total))
        self.stat_labels["approved"].configure(text=str(approved))
        self.stat_labels["uploaded"].configure(text=str(uploaded))
        names = [entry.get("seo", {}).get("title", "Thiết kế chưa đặt tên")
                 for entry in list(self.records.values())[:3]]
        self.recent_text.configure(
            text="  •  ".join(names) if names else TEXT["empty"],
        )
        for child in self.library_list.winfo_children():
            child.destroy()
        if not self.records:
            self._label(self.library_list, TEXT["empty"], 12, fg=MUTED).pack(
                anchor="w", padx=10, pady=12,
            )
        for entry in list(self.records.values())[:120]:
            is_selected = entry["id"] == self.selected_id
            title = entry.get("seo", {}).get("title", "Thiết kế chưa có tên")
            state = status_label(entry.get("platform_status", {}).get(
                self.platform.get(), "draft"
            ))
            short = title[:76] + ("…" if len(title) > 76 else "")
            button = ctk.CTkButton(
                self.library_list,
                text=f"{short}    ·    {state}",
                height=39, anchor="w", corner_radius=9,
                fg_color="#1C4F56" if is_selected else CARD_ALT,
                hover_color="#215263", text_color=WHITE,
                font=self._font(12),
                command=lambda design_id=entry["id"]: self._select(design_id),
            )
            button.pack(fill="x", padx=6, pady=3)
        self._update_inspector()

    def _select(self, design_id: str) -> None:
        self.selected_id = design_id
        self.refresh()

    def _selected(self) -> dict | None:
        entry = self.records.get(self.selected_id or "")
        if entry is None:
            messagebox.showinfo("Chọn thiết kế", TEXT["no_selection"])
        return entry

    def _update_inspector(self) -> None:
        entry = self.records.get(self.selected_id or "")
        if entry is None:
            self.detail_name.configure(text=TEXT["empty"])
            self.detail_status.configure(text="")
            self.detail_warning.configure(text="")
            self.art_preview.configure(text="CHƯA CHỌN ẢNH", image=None)
            return
        self.detail_name.configure(text=entry.get("seo", {}).get("title", "Thiết kế"))
        state = entry.get("platform_status", {}).get(self.platform.get(), "draft")
        self.detail_status.configure(text=PLATFORMS[self.platform.get()] + ": " + status_label(state))
        self.detail_warning.configure(text=entry.get("quality_warning", "")[:185])
        image_path = Path(entry.get("source_file", ""))
        try:
            with Image.open(image_path) as original:
                thumb = original.convert("RGBA")
                thumb.thumbnail((130, 130))
                background = Image.new("RGBA", (140, 140), "#E6ECEF")
                background.alpha_composite(thumb, ((140-thumb.width)//2, (140-thumb.height)//2))
                self.preview_image = ctk.CTkImage(
                    light_image=background.convert("RGB"),
                    dark_image=background.convert("RGB"),
                    size=(140, 140),
                )
            self.art_preview.configure(text="", image=self.preview_image)
        except (OSError, ValueError):
            self.art_preview.configure(text="Không xem được ảnh", image=None)

    def _run(self, status: str, fn, *args, **kwargs) -> None:
        if self.busy:
            messagebox.showinfo("Đang xử lý", "Đã có tác vụ chạy. Vui lòng hoàn tất tác vụ hiện tại.")
            return
        self.busy = True
        self.message.set(status)

        def worker() -> None:
            try:
                result = fn(*args, **kwargs)
                self.events.put(("ok", result))
            except Exception as exc:
                self.events.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_events(self) -> None:
        try:
            while True:
                kind, result = self.events.get_nowait()
                self.busy = False
                if kind == "ok":
                    self.message.set("✓  Đã hoàn tất. Dữ liệu được lưu trên máy.")
                    self.refresh()
                    if isinstance(result, dict) and "id" in result:
                        self.selected_id = result["id"]
                        self.refresh()
                    if isinstance(result, list):
                        self._show_trends(result)
                else:
                    self.message.set("Lỗi xử lý. Thiết kế hiện có được giữ nguyên.")
                    messagebox.showerror("Không thể thực hiện", str(result))
        except queue.Empty:
            pass
        self.after(120, self._handle_events)

    def generate(self) -> None:
        prompt = self.prompt_box.get("1.0", "end").strip()
        niche = self.niche.get().strip()
        keywords = self.keywords.get().strip()
        if len(prompt) < 5 or not niche:
            messagebox.showwarning("Thiếu thông tin", "Hãy nhập prompt và chủ đề thiết kế.")
            return
        if find_blocked_terms(f"{prompt} {niche} {keywords}", get_blocklist()):
            messagebox.showerror("Cảnh báo từ khóa", "Nội dung có từ khóa cần kiểm tra bản quyền.")
            return
        if not messagebox.askyesno("Xác nhận quyền sử dụng", TEXT["rights"]):
            return
        model_id = LABELS.get(self.model.get(), "")
        if not model_id:
            messagebox.showerror("Model chưa hỗ trợ", "Vui lòng chọn model trong danh sách.")
            return
        spec = get_spec(model_id)
        seo_mode = "gemini" if self.seo.get().startswith("Gemini") else "local"
        if spec.paid or seo_mode == "gemini":
            if not messagebox.askyesno(
                "Xác nhận có thể phát sinh phí",
                f"Model: {spec.label}\nSEO Gemini: {'Bật' if seo_mode == 'gemini' else 'Tắt'}\n\n"
                "Lệnh này có thể trừ tiền hoặc tín dụng ở tài khoản API của bạn. "
                "Không tự chuyển nhà cung cấp và không tự thử lại yêu cầu có tính phí.\n\n"
                + TEXT["paid"],
            ):
                return
        try:
            provider = make_provider(
                model_id, {key: variable.get() for key, variable in self.keys.items()},
                allow_paid=spec.paid, gemini_size=self.resolution.get(),
            )
        except (ValueError, PermissionError) as exc:
            messagebox.showerror("Thiếu cấu hình API", str(exc))
            self.show_page("settings")
            return
        key = self.keys["GEMINI_API_KEY"].get()
        self._run("Đang tạo hình ảnh và dữ liệu SEO...", create_draft,
                  prompt, niche, keywords, provider, seo_mode, key)

    def import_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Chọn ảnh thiết kế trên máy",
            filetypes=[("Ảnh PNG / JPG / WebP", "*.png *.jpg *.jpeg *.webp")],
        )
        if path:
            self._run("Đang nhập file, không gọi API tạo ảnh...",
                      import_design, Path(path), self.niche.get(), self.keywords.get())

    def fetch_trends(self) -> None:
        self._run("Đang tải Google Trends RSS...",
                  read_trends, self.country.get(), 15)

    def _show_trends(self, trends) -> None:
        for child in self.trend_rows.winfo_children():
            child.destroy()
        if not trends:
            self._label(self.trend_rows, "Nguồn RSS không có dữ liệu trong đợt tải này.",
                        12, fg=MUTED).pack(anchor="w", padx=10, pady=10)
        for trend in trends:
            row = ctk.CTkFrame(self.trend_rows, fg_color=CARD_ALT, corner_radius=11)
            row.pack(fill="x", padx=5, pady=5)
            self._label(row, trend.title, 13, bold=True).pack(
                anchor="w", padx=14, pady=(10, 2),
            )
            self._label(row, f"Lượt quan tâm: {trend.approx_traffic}  ·  {trend.published}",
                        10, fg=MUTED).pack(anchor="w", padx=14, pady=(0, 8))
            self._button(
                row, "Sao chép chủ đề",
                lambda topic=trend.title: self._copy(topic), width=152,
            ).pack(anchor="e", padx=12, pady=(0, 10))

    def _copy(self, value: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(value)
        self.message.set("Đã sao chép. Hãy kiểm tra nhãn hiệu trước khi sử dụng.")

    @staticmethod
    def _open_file(path: Path) -> None:
        if os.name == "nt":
            os.startfile(path)
        else:
            webbrowser.open(path.resolve().as_uri())

    def open_png(self) -> None:
        if entry := self._selected():
            self._open_file(Path(entry["print_file"]))

    def preflight(self) -> None:
        if not (entry := self._selected()):
            return
        platform = self.platform.get()

        def inspect():
            with Image.open(entry["print_file"]) as original:
                checks = audit_image(original, platform)
            lines = [
                f"{x.level.upper()} · {x.name} · {x.message}"
                for x in checks
            ]
            return "\n".join(lines)

        # The quality scan can be expensive on a 5000x5500 PNG.
        self._run("Đang kiểm tra thông số ảnh in...",
                  self._show_quality, inspect)

    def _show_quality(self, inspect) -> dict:
        report = inspect()
        self.events.put(("quality", report))
        return {}

    def preview_colors(self) -> None:
        if not (entry := self._selected()):
            return
        source = Path(entry["print_file"])
        target = source.parent / "preview-4-colors.png"

        def work():
            with Image.open(source) as original:
                original.thumbnail((1000, 1000))
                make_color_preview(original, target)
            return {}

        self._run("Đang tạo ảnh xem trước trên 4 màu áo...", work)

    def edit_seo(self) -> None:
        if not (entry := self._selected()):
            return
        popup = ctk.CTkToplevel(self)
        popup.title("Chỉnh sửa SEO · PODBot")
        popup.geometry("670x555")
        popup.configure(fg_color=BG)
        popup.transient(self)
        popup.grab_set()
        seo = entry["seo"]
        self._label(popup, "Chỉnh sửa nội dung sản phẩm", 21, bold=True).pack(
            anchor="w", padx=23, pady=(23, 15),
        )
        self._label(popup, "Tiêu đề", 12, fg=MUTED).pack(
            anchor="w", padx=23,
        )
        title = ctk.CTkEntry(popup, height=40, fg_color=CARD, border_color=BORDER)
        title.pack(fill="x", padx=23, pady=(5, 12))
        title.insert(0, seo["title"])
        self._label(popup, "Mô tả", 12, fg=MUTED).pack(anchor="w", padx=23)
        description = ctk.CTkTextbox(popup, height=125, fg_color=CARD,
                                     border_color=BORDER, border_width=1)
        description.pack(fill="x", padx=23, pady=(5, 12))
        description.insert("1.0", seo["description"])
        self._label(popup, "Thẻ tags (phân tách bằng dấu phẩy)", 12, fg=MUTED).pack(
            anchor="w", padx=23,
        )
        tags = ctk.CTkTextbox(popup, height=70, fg_color=CARD,
                               border_color=BORDER, border_width=1)
        tags.pack(fill="x", padx=23, pady=(5, 15))
        tags.insert("1.0", ", ".join(seo["tags"]))

        def save() -> None:
            try:
                update_seo(entry["id"], title.get(),
                           description.get("1.0", "end").strip(),
                           tags.get("1.0", "end").split(","))
            except (OSError, ValueError) as exc:
                messagebox.showerror("Không lưu được SEO", str(exc), parent=popup)
                return
            popup.destroy()
            self.refresh()
            self.message.set("Đã lưu SEO. Nếu đã duyệt trước đó, phải duyệt lại.")

        self._button(popup, "Lưu thay đổi", save, primary=True, width=175).pack(
            anchor="e", padx=23, pady=(0, 20),
        )

    def process_image(self) -> None:
        if not (entry := self._selected()):
            return
        remove = messagebox.askyesno(
            "Xóa nền tùy chọn",
            "Bạn đã cài rembg và muốn sử dụng? Công cụ bên ngoài có thể tải model "
            "lần đầu tiên. Chọn Không để chỉ cắt và căn lề bằng Pillow.",
        )
        rembg = None
        if remove:
            file = filedialog.askopenfilename(title="Chọn file rembg.exe")
            if not file:
                return
            rembg = Path(file)
        upscale = messagebox.askyesno(
            "Phóng to bằng Real-ESRGAN",
            "Bạn muốn sử dụng Real-ESRGAN đã cài riêng? "
            "Chọn Không để dùng phép nội suy Lanczos.",
        )
        esrgan = None
        if upscale:
            file = filedialog.askopenfilename(title="Chọn Real-ESRGAN executable")
            if not file:
                return
            esrgan = Path(file)
        if not messagebox.askyesno(
            "Tạo lại file in", "Xử lý từ ảnh gốc sẽ tạo file mới "
            "và hủy trạng thái đã duyệt. Tiếp tục?",
        ):
            return
        options = ProcessOptions(
            remove_background=remove, rembg_binary=rembg,
            upscale=upscale, esrgan_binary=esrgan,
        )
        self._run("Đang xử lý lại ảnh gốc...",
                  process_stored_design, entry["id"], options)

    def approve(self) -> None:
        if not (entry := self._selected()):
            return
        platform = self.platform.get()
        if not entry.get("rights_confirmed_at"):
            if not messagebox.askyesno(
                "Xác nhận quyền bán thương mại",
                "Tôi xác nhận có quyền sử dụng thiết kế này để bán, đã rà soát "
                "nội dung, nhãn hiệu, chính sách nền tảng và file in.",
            ):
                return
            try:
                confirm_rights(entry["id"])
            except (OSError, ValueError) as exc:
                messagebox.showerror("Không xác nhận được", str(exc))
                return
        self._run("Đang đánh giá chất lượng và xét duyệt...",
                  approve_listing, entry["id"], platform)

    def open_store(self) -> None:
        if not (entry := self._selected()):
            return
        platform = self.platform.get()
        if entry.get("platform_status", {}).get(platform) != "approved":
            messagebox.showwarning("Chưa được duyệt",
                                   "Bạn phải phê duyệt thiết kế cho sàn này trước.")
            return
        messagebox.showinfo(
            "Đăng bán thủ công",
            "Ứng dụng mở trang chính sách và trang bán hàng. "
            "Bạn cần tự tải PNG lên, kiểm tra vị trí, giá, tags và xác nhận.",
        )
        webbrowser.open(POLICY_URLS[platform])
        webbrowser.open(UPLOADER[platform])

    def mark_uploaded(self) -> None:
        if not (entry := self._selected()):
            return
        platform = self.platform.get()
        if entry.get("platform_status", {}).get(platform) != "approved":
            messagebox.showwarning("Chưa duyệt", "Hãy phê duyệt trước khi đánh dấu đã đăng.")
            return
        if messagebox.askyesno(
            "Xác nhận đã đăng",
            "Bạn đã đăng đúng thiết kế này trên "
            + PLATFORMS[platform] + " và kiểm tra trong tài khoản người bán?",
        ):
            self._run("Đang xác nhận trạng thái đăng bán...",
                      mark_uploaded, entry["id"], platform, confirmed=True)

    def export(self) -> None:
        target = filedialog.asksaveasfilename(
            title="Xuất danh sách đã duyệt",
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile=f"podbot-{self.platform.get()}-approved.csv",
        )
        if target:
            try:
                n = export_csv(Path(target), self.platform.get())
            except (OSError, ValueError, RuntimeError) as exc:
                messagebox.showerror("Không xuất được dữ liệu", str(exc))
                return
            messagebox.showinfo("Xuất CSV thành công",
                                f"Đã xuất {n} thiết kế đã duyệt.")

    def edit_blocklist(self) -> None:
        path = data_directory() / "blocklist.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(
                "# Mỗi dòng là một từ khóa cần rà soát, không phải dữ liệu nhãn hiệu chính thức.\n",
                encoding="utf-8",
            )
        self._open_file(path)


def main() -> None:
    PODBotDesktop().mainloop()


if __name__ == "__main__":
    main()
