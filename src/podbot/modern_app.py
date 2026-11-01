"""PODBot Studio: modern Vietnamese-first CustomTkinter desktop shell.

Existing providers, image processing, quality gates, and publishing stay in independent
modules. No network calls on the UI thread. Never store API keys or auto-post to stores.
"""

from __future__ import annotations

import hashlib
import os
import queue
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from podbot.api_limits import get_daily_limit, set_daily_limit
from podbot.audit import find_blocked_terms, get_blocklist, make_color_preview
from podbot.credential_vault import erase_credentials, remember_credentials, restore_credentials
from podbot.importer import import_design
from podbot.job_queue import JobQueue
from podbot.mockups import create_shirt_mockup
from podbot.model_discovery import PROVIDER_KEYS, discover_models
from podbot.offline_tasks import execute_next
from podbot.pipeline import create_draft
from podbot.prompt_recipe import PromptRecipe, build_prompt
from podbot.provider_catalog import LABELS, get_spec, make_provider, set_discovered_models
from podbot.storage import list_designs
from podbot.studio_actions import StudioActions
from podbot.studio_pages import StudioPages, model_options, status_label
from podbot.studio_theme import (
    ACCENT,
    ACCENT_HOVER,
    ACCENT_TEXT,
    BG,
    BORDER,
    CARD,
    CARD_ALT,
    MENU,
    MUTED,
    N_FONT,
    PLATFORMS,
    SIDEBAR,
    STATUSES,
    TEXT,
    WHITE,
)
from podbot.trends import read_trends

__all__ = ["ACCENT", "MENU", "STATUSES", "TEXT", "PODBotDesktop", "model_options", "status_label"]

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")



class PODBotDesktop(StudioPages, StudioActions, ctk.CTk):
    """Single-window, five-page navigation and event-driven background work."""

    def __init__(self) -> None:
        super().__init__()
        self.title("PODBot Studio · Giao diện tiếng Việt")
        self.geometry("1240x790")
        self.minsize(940, 660)
        self.configure(fg_color=BG)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.offline_jobs = JobQueue()
        self.offline_jobs.recover()
        self.busy = False
        self.records: dict[str, dict] = {}
        self.selected_id: str | None = None
        self.preview_image: ctk.CTkImage | None = None
        self.current_page = "overview"
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        self.pages: dict[str, ctk.CTkScrollableFrame] = {}

        self.model = tk.StringVar(value="Hãy kiểm tra API key trong Cài đặt")
        self.api_discovery_vendor = tk.StringVar(value="openai")
        self.verified_provider_keys: dict[str, str] = {}
        self.verified_model_choices: dict[str, set[str]] = {}
        self.manual_models_enabled = False
        self.seo = tk.StringVar(value="SEO offline (miễn phí)")
        self.resolution = tk.StringVar(value="2K")
        self.flat_background_prompt = tk.BooleanVar(value=True)
        self.recipe_subject = tk.StringVar(value="minimalist mountain sunrise")
        self.recipe_style = tk.StringVar(value="minimal-vector")
        self.recipe_layout = tk.StringVar(value="centered")
        self.recipe_palette = tk.StringVar(value="#123047, #F4AC45, #F5F0DE")
        self.recipe_background = tk.StringVar(value="transparent")
        self.recipe_lettering = tk.StringVar(value="none")
        self.recipe_text = tk.StringVar(value="")
        self._built_recipe: dict | None = None
        self._built_prompt: str = ""
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
        try:
            cap = get_daily_limit()
        except (ValueError, RuntimeError):
            cap = 0  # Malformed config must default to no paid calls.
        self.paid_calls_cap = tk.StringVar(value=str(cap))
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
        self._label(brand, "STUDIO  1.0 PREVIEW 3  •  VI", 11, fg=ACCENT, bold=True).pack(
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

    def save_api_cap(self) -> None:
        try:
            set_daily_limit(int(self.paid_calls_cap.get()))
            self.message.set("Đã lưu hạn mức số lượt API có thể tính phí.")
        except (ValueError, OSError) as exc:
            messagebox.showerror("Hạn mức API không hợp lệ", str(exc))

    def store_api_keys(self) -> None:
        if not messagebox.askyesno(
            "Lưu API key vào Windows Credential Manager",
            "Chỉ lưu các key đang nhập trên máy này, bằng kho lưu trữ hệ điều hành. "
            "Bạn có thể xóa bất cứ lúc nào. Đồng ý lưu?",
        ):
            return
        try:
            count = remember_credentials(
                {name: variable.get() for name, variable in self.keys.items()},
                confirmed=True,
            )
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Không lưu được API key", str(exc))
            return
        messagebox.showinfo("Kho khóa Windows", f"Đã lưu {count} API key.")

    def restore_api_keys(self) -> None:
        if not messagebox.askyesno(
            "Khôi phục API key", "Lấy các API key từ Windows Credential Manager vào phiên chạy này?",
        ):
            return
        try:
            found = restore_credentials(confirmed=True)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Không đọc được kho khóa", str(exc))
            return
        for name, key in found.items():
            self.keys[name].set(key)
        self.message.set(f"Đã khôi phục {len(found)} API key từ Windows.")

    def clear_api_keys(self) -> None:
        if not messagebox.askyesno(
            "Xóa API key đã lưu", "Xóa toàn bộ API key của PODBot đã lưu trong Windows?",
        ):
            return
        try:
            removed = erase_credentials(confirmed=True)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Không xóa được kho khóa", str(exc))
            return
        self.message.set(f"Đã xóa {removed} API key trong kho Windows.")

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
            except Exception as exc:  # noqa: BLE001
                self.events.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_events(self) -> None:
        try:
            while True:
                kind, result = self.events.get_nowait()
                self.busy = False
                if kind == "quality":
                    messagebox.showinfo(
                        "Kết quả kiểm tra chất lượng",
                        str(result) + "\n\nCác kiểm tra FAIL cần xử lý trước khi phê duyệt.",
                    )
                    continue
                if kind == "ok":
                    self.message.set("✓  Đã hoàn tất. Dữ liệu được lưu trên máy.")
                    if isinstance(result, dict) and "_model_discovery" in result:
                        self._apply_discovery(result)
                    if isinstance(result, dict) and "_job_inspection" in result:
                        messagebox.showinfo("Kiểm tra ảnh + OCR", result["_job_inspection"])
                    self.refresh()
                    if isinstance(result, dict) and "id" in result:
                        self.selected_id = result["id"]
                        self.refresh()
                    if isinstance(result, Path) and result.suffix == ".svg":
                        self.message.set("Đã xuất SVG để kiểm tra: " + str(result))
                        messagebox.showinfo(
                            "SVG đã tạo (cần duyệt)",
                            f"File: {result}\nHãy xem lại đường nét, chữ và giấy phép "
                            "trước khi sử dụng. PNG đã duyệt bán không thay đổi.",
                        )
                    if isinstance(result, list):
                        self._show_trends(result)
                else:
                    self.message.set("Lỗi xử lý. Thiết kế hiện có được giữ nguyên.")
                    messagebox.showerror("Không thể thực hiện", str(result))
        except queue.Empty:
            pass
        self.after(120, self._handle_events)
        self._drain_offline_jobs()

    @staticmethod
    def _credential_fingerprint(provider: str, credentials: dict[str, str]) -> str:
        key = credentials.get(PROVIDER_KEYS[provider], "").strip()
        account = credentials.get("CLOUDFLARE_ACCOUNT_ID", "") if provider == "cloudflare" else ""
        return hashlib.sha256((provider + "\0" + account + "\0" + key).encode()).hexdigest()

    def check_provider_models(self) -> None:
        if self.busy:
            return
        provider = self.api_discovery_vendor.get()
        credentials = {name: field.get() for name, field in self.keys.items()}
        if not credentials.get(PROVIDER_KEYS[provider], "").strip():
            messagebox.showwarning("Thiếu API key", "Nhập key trước khi kiểm tra.")
            return
        fingerprint = self._credential_fingerprint(provider, credentials)

        def work():
            result = discover_models(provider, credentials)
            return {"_model_discovery": result, "_fingerprint": fingerprint}

        self._run("Đang xác minh key và lấy danh sách model (chỉ đọc)...", work)

    def _verified_model_labels(self) -> list[str]:
        current = {name: field.get() for name, field in self.keys.items()}
        selections: set[str] = set()
        for provider, fingerprint in self.verified_provider_keys.items():
            if fingerprint == self._credential_fingerprint(provider, current):
                selections.update(self.verified_model_choices.get(provider, set()))
        return [label for label, model_id in LABELS.items() if model_id in selections]

    def _apply_discovery(self, payload: dict) -> None:
        result = payload["_model_discovery"]
        current = {key: field.get() for key, field in self.keys.items()}
        if payload["_fingerprint"] != self._credential_fingerprint(result.provider, current):
            self.model_scan_status.configure(
                text="API key đã thay đổi trong lúc kiểm tra. Hãy kiểm tra lại.",
            )
            return
        if result.verified:
            self.verified_provider_keys[result.provider] = payload["_fingerprint"]
        else:
            self.verified_provider_keys.pop(result.provider, None)
        found = set_discovered_models(result.provider, result.models)
        self.verified_model_choices[result.provider] = (
            {spec.id for spec in found} if result.verified else set()
        )
        message = result.message
        if found:
            message += f"\n{len(found)} model tương thích được liệt kê, không thêm mục trùng."
        else:
            message += "\nKhông thấy model phù hợp trong trang đã kiểm tra."
        if result.provider in ("replicate", "cloudflare"):
            message += (
                "\nDanh sách API có thể chưa đầy đủ. Preset vẫn có thể chọn "
                "trong chế độ thủ công, nhưng chưa xác minh quyền sử dụng."
            )
        self.model_scan_status.configure(text=message)
        values = self._verified_model_labels()
        if self.manual_models_enabled:
            values = list(dict.fromkeys([*values, *model_options()]))
        if not values:
            values = ["Hãy kiểm tra API key trong Cài đặt"]
        self.model_dropdown.configure(values=values)
        self.model.set(values[0])
        self._model_changed(self.model.get())
        self.message.set("Đã kiểm tra key; chưa phát sinh lượt tạo ảnh tính phí.")

    def use_manual_model_presets(self) -> None:
        if not messagebox.askyesno(
            "Bật preset thủ công",
            "Danh sách preset là cấu hình mẫu, không xác minh quyền truy cập "
            "hoặc các thông số model mới. Mọi lần tạo ảnh tính phí vẫn cần "
            "xác nhận. Bạn muốn bật preset thủ công?",
        ):
            return
        self.manual_models_enabled = True
        choices = list(dict.fromkeys([*self._verified_model_labels(), *model_options()]))
        self.model_dropdown.configure(values=choices)
        self.model.set(choices[0])
        self._model_changed(self.model.get())

    def build_structured_prompt(self) -> None:
        """Build locally; never call a provider or consume an API attempt."""
        try:
            recipe = PromptRecipe(
                subject=self.recipe_subject.get(),
                style=self.recipe_style.get(),
                layout=self.recipe_layout.get(),
                colors=tuple(item.strip() for item in self.recipe_palette.get().split(",")),
                background=self.recipe_background.get(),
                text_rule=self.recipe_lettering.get(),
                original_text=self.recipe_text.get(),
            ).validated()
            assembled = build_prompt(recipe)
        except ValueError as exc:
            messagebox.showwarning("Cấu hình prompt chưa hợp lệ", str(exc))
            return
        self.prompt_box.delete("1.0", "end")
        self.prompt_box.insert("1.0", assembled)
        self._built_recipe = recipe.to_manifest()
        self._built_prompt = assembled
        # Background requirement is already part of the structured prompt.
        self.flat_background_prompt.set(False)
        self.message.set("Đã dựng prompt trên máy, 0 phí API. Hãy rà soát trước khi tạo ảnh.")

    def generate(self) -> None:
        prompt = self.prompt_box.get("1.0", "end").strip()
        niche = self.niche.get().strip()
        keywords = self.keywords.get().strip()
        recipe_data = self._built_recipe if prompt == self._built_prompt else None
        if (recipe_data and recipe_data["background"] == "transparent"
                and self.flat_background_prompt.get()):
            messagebox.showwarning(
                "Quy tắc nền mâu thuẫn",
                "Prompt yêu cầu alpha trong suốt nhưng hậu tố nền trắng phẳng đang bật. "
                "Hãy bỏ chọn hậu tố nền trắng trước khi gọi API.",
            )
            return
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
        confirmed_from_listing = model_id in self.verified_model_choices.get(
            spec.vendor, set()
        )
        if confirmed_from_listing or model_id.startswith("discovered:"):
            current = {name: field.get() for name, field in self.keys.items()}
            if (not confirmed_from_listing or self.verified_provider_keys.get(spec.vendor)
                    != self._credential_fingerprint(spec.vendor, current)):
                messagebox.showwarning(
                    "API key đã đổi", "Hãy kiểm tra lại key để cập nhật model khả dụng."
                )
                return
        elif not self.manual_models_enabled:
            messagebox.showwarning(
                "Model chưa kiểm tra", "Hãy kiểm tra API key hoặc bật preset thủ công."
            )
            return
        seo_mode = "gemini" if self.seo.get().startswith("Gemini") else "local"
        if (spec.paid or seo_mode == "gemini") and not messagebox.askyesno(
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
                  prompt, niche, keywords, provider, seo_mode, key,
                  flat_background_prompt=self.flat_background_prompt.get(),
                  prompt_recipe=recipe_data)

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
            blocked = find_blocked_terms(
                " ".join((trend.title, *trend.keywords)), get_blocklist()
            )
            row = ctk.CTkFrame(self.trend_rows, fg_color=CARD_ALT, corner_radius=11)
            row.pack(fill="x", padx=5, pady=5)
            self._label(row, trend.title, 13, bold=True).pack(
                anchor="w", padx=14, pady=(10, 2),
            )
            self._label(row, f"Lượt quan tâm: {trend.approx_traffic}  ·  {trend.published}",
                        10, fg=MUTED).pack(anchor="w", padx=14, pady=(0, 6))
            if blocked:
                self._label(
                    row, "⚠  Trùng blocklist: " + ", ".join(blocked[:5])
                    + " · Không tự điền vào thiết kế",
                    11, fg="#FFB867", wraplength=670,
                ).pack(anchor="w", padx=14, pady=(0, 5))
            keywords = ", ".join(trend.keywords[:8]) or "Chưa có từ khóa đủ tin cậy"
            self._label(row, f"Gợi ý từ khóa RSS: {keywords}",
                        11, fg=WHITE, wraplength=670, justify="left").pack(
                anchor="w", padx=14, pady=(0, 6),
            )
            if trend.news_titles:
                self._label(row, f"Bài báo liên quan: {trend.news_titles[0]}",
                            10, fg=MUTED, wraplength=680, justify="left").pack(
                    anchor="w", padx=14, pady=(0, 5),
                )
            controls = ctk.CTkFrame(row, fg_color="transparent")
            controls.pack(anchor="e", padx=12, pady=(0, 10))
            self._button(
                controls, "Sao chép từ khóa",
                lambda terms=trend.keywords: self._copy(", ".join(terms)), width=147,
            ).pack(side="left", padx=4)
            self._button(
                controls, "Dùng chủ đề + từ khóa",
                lambda selected=trend: self._use_trend(selected), width=180,
            ).pack(side="left", padx=4)
            if blocked:
                controls.winfo_children()[-1].configure(state="disabled")

    def _use_trend(self, trend) -> None:
        if not trend.keywords:
            messagebox.showinfo("Thiếu từ khóa", "Không có từ khóa đáng tin từ RSS.")
            return
        if find_blocked_terms(" ".join((trend.title, *trend.keywords)), get_blocklist()):
            messagebox.showwarning(
                "Từ khóa cần rà soát",
                "Xu hướng có từ khóa trong blocklist, không tự đưa vào mẫu thiết kế.",
            )
            return
        if not messagebox.askyesno(
            "Chuyển vào mẫu thiết kế",
            "Đây là từ khóa gợi ý từ tiêu đề RSS/bài báo, KHÔNG phải Related Queries "
            "được Google xác nhận. Xu hướng có thể chứa thương hiệu hoặc người thật.\n"
            "Bạn phải rà soát quyền thương mại và viết prompt riêng. Tiếp tục?",
        ):
            return
        self.niche.set(trend.title)
        self.keywords.set(", ".join(trend.keywords[:8]))
        self.show_page("create")
        self.message.set("Đã điền chủ đề và từ khóa. Chưa phát sinh yêu cầu AI hay phí API.")

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
        self.offline_jobs.enqueue(
            "inspect", {"design_id": entry["id"], "platform": self.platform.get()}
        )
        self.message.set("Đã thêm kiểm tra ảnh + OCR vào hàng đợi.")
        self._drain_offline_jobs()

    def _drain_offline_jobs(self) -> None:
        if self.busy or not any(job.status == "pending" for job in self.offline_jobs.list()):
            return
        self._run("Đang xử lý hàng đợi offline...", execute_next, self.offline_jobs)

    def show_jobs(self) -> None:
        jobs = self.offline_jobs.list()
        if not jobs:
            messagebox.showinfo("Hàng đợi tác vụ", "Chưa có tác vụ offline.")
            return
        popup = ctk.CTkToplevel(self)
        popup.title("Hàng đợi offline")
        popup.geometry("550x250")
        popup.transient(self)
        popup.grab_set()
        choices = {
            f"{job.id[:10]} · {job.kind} · {job.status} · {job.attempts}/{job.max_attempts}": job.id
            for job in jobs
        }
        selected = tk.StringVar(value=next(iter(choices)))
        self._label(popup, "Chọn tác vụ · Tạo ảnh AI không nằm trong hàng đợi này",
                    13, fg=MUTED).pack(padx=16, pady=(20, 12))
        ctk.CTkOptionMenu(popup, values=list(choices), variable=selected,
                          width=490).pack(padx=16)
        def change(action: str) -> None:
            job_id = choices[selected.get()]
            changed = (
                self.offline_jobs.retry(job_id) if action == "retry"
                else self.offline_jobs.cancel(job_id)
            )
            messagebox.showinfo("Hàng đợi", "Đã cập nhật." if changed else
                                "Không thể thay đổi tác vụ đang chạy/đã hoàn tất.",
                                parent=popup)
            popup.destroy()
            self._drain_offline_jobs()
        buttons = ctk.CTkFrame(popup, fg_color="transparent")
        buttons.pack(pady=22)
        self._button(buttons, "Thử lại", lambda: change("retry")).pack(side="left", padx=7)
        self._button(buttons, "Hủy chờ", lambda: change("cancel")).pack(side="left", padx=7)

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

    def preview_shirt(self) -> None:
        if not (entry := self._selected()):
            return
        target = Path(entry["print_file"]).parent / "mockup-shirt.png"

        def worker():
            with Image.open(entry["print_file"]) as original:
                original.thumbnail((960, 960))
                create_shirt_mockup(original, target)
            return {}

        self._run("Đang tạo mô phỏng áo thun...", worker)



def main() -> None:
    PODBotDesktop().mainloop()


if __name__ == "__main__":
    main()
