"""CustomTkinter page construction, labels and model UI for PODBot Studio."""

from __future__ import annotations

import os

import customtkinter as ctk

from podbot.provider_catalog import CATALOG, GEMINI_IMAGE_SIZE_MODELS, LABELS, get_spec
from podbot.settings import data_directory
from podbot.studio_theme import (
    ACCENT,
    ACCENT_HOVER,
    BG,
    BORDER,
    CARD_ALT,
    MUTED,
    PLATFORMS,
    STATUSES,
    WARNING,
    WHITE,
)


def model_options() -> list[str]:
    return [spec.label for spec in CATALOG]


def status_label(state: str) -> str:
    return STATUSES.get(state, state)


class StudioPages:
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
            "centered composition for T-shirt print, no lettering, no logos",
        )
        builder = ctk.CTkFrame(form, fg_color=CARD_ALT, corner_radius=11)
        builder.pack(fill="x", padx=20, pady=(13, 4))
        self._label(
            builder, "BỘ DỰNG PROMPT CÓ CẤU TRÚC · OFFLINE", 11, bold=True, fg=ACCENT,
        ).pack(anchor="w", padx=13, pady=(12, 4))
        self._label(
            builder, "Không cần GPU, không gửi API. Dựng prompt rồi kiểm tra trước khi tạo ảnh.",
            10, fg=MUTED, wraplength=670,
        ).pack(anchor="w", padx=13, pady=(0, 7))
        inputs = ctk.CTkFrame(builder, fg_color="transparent")
        inputs.pack(fill="x", padx=13)
        inputs.grid_columnconfigure((0, 1), weight=1)
        fields_spec = (
            ("CHỦ THỂ", self.recipe_subject),
            ("BẢNG MÀU (1-6 mã #RRGGBB)", self.recipe_palette),
            ("CHỮ GỐC (NẾU CHỌN ORIGINAL)", self.recipe_text),
        )
        for index, (label, variable) in enumerate(fields_spec):
            panel = ctk.CTkFrame(inputs, fg_color="transparent")
            panel.grid(row=index, column=0, columnspan=2, sticky="ew", pady=(1, 5))
            self._label(panel, label, 10, fg=MUTED).pack(anchor="w", pady=(0, 3))
            ctk.CTkEntry(
                panel, textvariable=variable, height=33, fg_color=BG,
                border_color=BORDER, text_color=WHITE,
            ).pack(fill="x")
        dropdowns = (
            ("PHONG CÁCH", self.recipe_style,
             ["minimal-vector", "line-art", "vintage-screenprint", "paper-cut"]),
            ("BỐ CỤC", self.recipe_layout, ["centered", "badge", "stacked"]),
            ("NỀN", self.recipe_background, ["transparent", "flat-white"]),
            ("QUY TẮC CHỮ", self.recipe_lettering, ["none", "original"]),
        )
        for index, (label, variable, choices) in enumerate(dropdowns):
            panel = ctk.CTkFrame(inputs, fg_color="transparent")
            panel.grid(row=3 + index // 2, column=index % 2, sticky="ew",
                       padx=(0, 6) if index % 2 == 0 else (6, 0), pady=4)
            self._label(panel, label, 10, fg=MUTED).pack(anchor="w", pady=(0, 3))
            ctk.CTkOptionMenu(
                panel, values=choices, variable=variable, height=34,
                fg_color=BG, button_color=BORDER, text_color=WHITE,
            ).pack(fill="x")
        self._button(
            builder, "✦  Dựng prompt (0 phí API)", self.build_structured_prompt,
            width=245,
        ).pack(anchor="e", padx=13, pady=(9, 13))

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
            form, values=["Hãy kiểm tra API key trong Cài đặt"], variable=self.model,
            height=42, corner_radius=10, fg_color=CARD_ALT,
            button_color="#284C64", button_hover_color=BORDER,
            text_color=WHITE, font=self._font(12),
            command=self._model_changed,
        )
        self.model_dropdown.pack(fill="x", padx=20)
        self._button(
            form, "Chọn preset thủ công (chưa xác minh quyền)",
            self.use_manual_model_presets, width=280,
        ).pack(anchor="e", padx=20, pady=(8, 0))

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
        ctk.CTkCheckBox(
            form, text="Thêm gợi ý nền trắng phẳng để dễ tách nền (bật/tắt)",
            variable=self.flat_background_prompt, onvalue=True, offvalue=False,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color=WHITE, font=self._font(12),
        ).pack(anchor="w", padx=20, pady=(12, 0))
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
            hint = spec.hint
            if spec.vendor == "gemini" and spec.model not in GEMINI_IMAGE_SIZE_MODELS:
                hint += (
                    "  •  Model mới: chưa rõ hỗ trợ độ phân giải. "
                    "Không gửi imageSize/aspectRatio; dùng đầu ra mặc định."
                )
            self.model_explanation.configure(
                text=f"ℹ  {pricing}  •  {hint}  •  API key: {spec.env_key}",
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
        self._button(row, "◷  Hàng đợi", self.show_jobs, width=126).pack(
            side="left", padx=(9, 0)
        )
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
        for column in range(3):
            edits.grid_columnconfigure(column, weight=1)
        for index, (title, cmd) in enumerate((
            ("Xem PNG", self.open_png),
            ("Chỉnh SEO", self.edit_seo),
            ("Kiểm tra chất lượng", self.preflight),
            ("Xử lý lại ảnh", self.process_image),
            ("Xem màu áo", self.preview_colors),
            ("Mockup áo thun", self.preview_shirt),
        )):
            self._button(edits, title, cmd, width=130).grid(
                row=index // 3, column=index % 3, sticky="ew",
                padx=4, pady=(0, 8),
            )
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
            "Đọc chủ đề + gợi ý từ khóa từ Google Trends RSS/tin liên quan. "
            "Từ khóa không phải Google Related Queries; kiểm tra thương hiệu trước khi dùng.",
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
        self._label(results, "Chủ đề và từ khóa gợi ý từ RSS", 17, bold=True).pack(
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
        key_check = self._card(page)
        key_check.pack(fill="x", padx=8, pady=(0, 14))
        self._label(
            key_check, "KIỂM TRA API KEY & DÒ MODEL MỚI", 15, bold=True,
        ).pack(anchor="w", padx=20, pady=(16, 7))
        self._label(
            key_check,
            "Chỉ đọc danh sách model/định danh tài khoản, không tạo ảnh và không "
            "cố tính phí. Model được liệt kê chưa chắc có quyền dùng hay hỗ trợ PNG alpha.",
            11, fg=MUTED, wraplength=720,
        ).pack(anchor="w", padx=20, pady=(0, 9))
        check_row = ctk.CTkFrame(key_check, fg_color="transparent")
        check_row.pack(fill="x", padx=20, pady=(0, 9))
        ctk.CTkOptionMenu(
            check_row, values=["openai", "gemini", "replicate", "cloudflare",
                               "huggingface", "stability", "fal"],
            variable=self.api_discovery_vendor, width=165, fg_color=CARD_ALT,
            text_color=WHITE,
        ).pack(side="left", padx=(0, 9))
        self._button(
            check_row, "Kiểm tra key + tải model", self.check_provider_models,
            width=230, primary=True,
        ).pack(side="left")
        self.model_scan_status = self._label(
            key_check, "Chưa kiểm tra key nào. Không tự dùng model mặc định.",
            11, fg=WARNING, wraplength=690, justify="left",
        )
        self.model_scan_status.pack(anchor="w", padx=20, pady=(2, 17))
        limits = self._card(page)
        limits.pack(fill="x", padx=8, pady=(0, 14))
        self._label(limits, "GIỚI HẠN API VÀ KHO KHÓA WINDOWS", 14, bold=True).pack(
            anchor="w", padx=20, pady=(16, 8),
        )
        self._label(
            limits,
            "Số lượt GỌI API có thể tính phí tối đa mỗi nhà cung cấp trong một ngày "
            "(tính cả Gemini SEO). Đây KHÔNG phải hạn mức USD hay số tiền đã trừ; "
            "hãy đặt hạn mức tiền thật ở dashboard nhà cung cấp.",
            11, fg=MUTED, wraplength=720,
        ).pack(anchor="w", padx=20, pady=(0, 9))
        row = ctk.CTkFrame(limits, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 12))
        ctk.CTkEntry(
            row, textvariable=self.paid_calls_cap, width=80, height=37,
            fg_color=BG, border_color=BORDER,
        ).pack(side="left", padx=(0, 8))
        self._button(row, "Lưu giới hạn ngày", self.save_api_cap, width=175).pack(side="left")
        self._label(
            limits, "Tính theo ngày địa phương của Windows, không phải UTC. Mặc định 3 lượt / nhà cung cấp / ngày; 0 sẽ chặn mọi API tính phí. "
            "Tác vụ đã gửi không được hoàn lượt vì có thể đã bị tính tiền.",
            11, fg=WARNING, wraplength=720,
        ).pack(anchor="w", padx=20, pady=(0, 13))
        if os.getenv("PODBOT_PAID_CALLS_PER_DAY") is not None:
            self._label(
                limits,
                "⚠ Biến môi trường PODBOT_PAID_CALLS_PER_DAY = "
                + os.getenv("PODBOT_PAID_CALLS_PER_DAY", "")
                + " đang GHI ĐÈ hạn mức trong giao diện.",
                11, fg=WARNING, wraplength=720,
            ).pack(anchor="w", padx=20, pady=(0, 13))
        actions = ctk.CTkFrame(limits, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(0, 19))
        for label, callback in (
            ("Lưu key vào Windows", self.store_api_keys),
            ("Khôi phục key", self.restore_api_keys),
            ("Xóa key đã lưu", self.clear_api_keys),
        ):
            self._button(actions, label, callback, width=170).pack(
                side="left", padx=(0, 9),
            )
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

