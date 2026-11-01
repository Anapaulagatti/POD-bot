"""Design-management actions for the desktop Studio.

UI shell stays in modern_app.py; this mixin owns library operations.
No scheduled paid provider API calls are introduced.
"""

from __future__ import annotations

import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from podbot.processing import ProcessOptions, background_module_available, process_stored_design
from podbot.publishing import POLICY_URLS, approve_listing, confirm_rights, mark_uploaded
from podbot.settings import data_directory
from podbot.storage import export_csv, update_seo
from podbot.studio_theme import BG, BORDER, CARD, MUTED, PLATFORMS, UPLOADER
from podbot.vector_export import export_vector


class StudioActions:
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
        flat = messagebox.askyesno(
            "Tách nền phẳng bằng Pillow, có sẵn trong EXE",
            "Ảnh có nền trắng/màu phẳng gần đồng nhất?\n"
            "Có = dùng flood-fill từ các mép, không cần API/ML.\n"
            "Không = chọn rembg (nếu có) hoặc giữ nguyên nền.\n"
            "Lưu ý: kiểm tra kỹ chữ trắng, nét mảnh và quầng viền sau tách.",
        )
        remove, rembg = False, None
        if not flat:
            available = background_module_available()
            remove = messagebox.askyesno(
                "Tách nền AI rembg tùy chọn",
                "rembg Python đã cài: " + ("Có" if available else "Chưa") + ".\n"
                "Có = dùng rembg (có thể tải model lần đầu). "
                "Không = chỉ chuẩn hóa/căn lề file in.",
            )
            if remove and not available:
                if not messagebox.askyesno(
                    "Chưa có rembg trong EXE",
                    "Bạn có rembg.exe cài riêng? Chọn Có để duyệt file. "
                    "Nếu chạy mã nguồn có thể pip install -e \".[bg]\".",
                ):
                    return
                chosen = filedialog.askopenfilename(title="Chọn rembg.exe đã cài riêng")
                if not chosen:
                    return
                rembg = Path(chosen)
        upscale = messagebox.askyesno(
            "Phóng to bằng Real-ESRGAN",
            "Bạn muốn sử dụng Real-ESRGAN đã cài riêng? "
            "Chọn Không để dùng Lanczos.",
        )
        esrgan = None
        if upscale:
            chosen = filedialog.askopenfilename(title="Chọn Real-ESRGAN executable")
            if not chosen:
                return
            esrgan = Path(chosen)
        previous = [
            f"{platform}: {state}"
            for platform, state in entry.get("platform_status", {}).items()
            if state in ("approved", "uploaded")
        ]
        details = ", ".join(previous) if previous else "Chưa có duyệt đang hoạt động"
        if not messagebox.askyesno(
            "Xác nhận hủy trạng thái duyệt",
            f"Trạng thái hiện tại: {details}.\n"
            "Tạo lại file in sẽ chuyển cả Redbubble và TeePublic về DRAFT, "
            "kể cả khi đã ghi nhận UPLOADED. Việc xếp hàng có thể chạy sau.\n"
            "Hãy kiểm tra lại file in và duyệt lại trước khi bán. Đồng ý?",
        ):
            return
        options = ProcessOptions(
            flat_background=flat, remove_background=remove,
            rembg_binary=rembg, upscale=upscale, esrgan_binary=esrgan,
        )
        if not remove and not upscale:
            self.offline_jobs.enqueue(
                "reprocess", {"design_id": entry["id"], "flat_background": flat}
            )
            self.message.set("Đã thêm tác vụ xử lý ảnh vào hàng đợi an toàn.")
            self._drain_offline_jobs()
            return
        self._run(
            "Đang cắt nền / tạo lại file in...",
            process_stored_design, entry["id"], options,
        )

    def export_svg(self) -> None:
        if not (entry := self._selected()):
            return
        if not messagebox.askyesno(
            "Xuất SVG tùy chọn (CPU)",
            "Chỉ dành cho thiết kế ít màu. Bạn cần tự cài và chọn VTracer CLI "
            "từ nguồn tin cậy. SVG phải được xem lại và không thay đổi trạng thái "
            "duyệt PNG. Có thể mất thời gian trên máy yếu. Tiếp tục?",
        ):
            return
        executable = filedialog.askopenfilename(
            title="Chọn VTracer CLI đã cài riêng",
            filetypes=[("Windows executable", "*.exe"), ("Tất cả file", "*.*")],
        )
        if not executable:
            return
        self._run("Đang dựng SVG bằng VTracer CPU...", export_vector,
                  entry["id"], Path(executable))

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

