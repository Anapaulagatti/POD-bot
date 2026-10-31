"""Native Windows-friendly Tkinter GUI. Network calls run on background threads."""

from __future__ import annotations

import os
import queue
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image

from podbot.audit import (
    audit_image,
    find_blocked_terms,
    get_blocklist,
    make_color_preview,
    near_duplicates,
)
from podbot.importer import import_design
from podbot.mockups import create_shirt_mockup
from podbot.pipeline import create_draft
from podbot.processing import ProcessOptions, process_stored_design
from podbot.provider_catalog import CATALOG, LABELS, get_spec, make_provider
from podbot.publishing import POLICY_URLS, approve_listing, confirm_rights, mark_uploaded
from podbot.settings import data_directory
from podbot.storage import export_csv, list_designs, update_seo
from podbot.trends import read_trends

UPLOAD_PAGES = {
    "redbubble": "https://www.redbubble.com/portfolio/images/new",
    "teepublic": "https://www.teepublic.com/",
}


class PODBotApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PODBot Studio v4.0 | Model Marketplace")
        self.geometry("980x720")
        self.minsize(780, 600)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.records: dict[str, dict] = {}
        self.provider_choice = tk.StringVar(value=CATALOG[0].label)
        self.gemini_size = tk.StringVar(value="2K")
        self.seo_choice = tk.StringVar(value="Offline SEO")
        self.niche = tk.StringVar(value="minimalist nature")
        self.keywords = tk.StringVar(value="mountain silhouette, hiking, adventure")
        self.account_id = tk.StringVar(value=os.getenv("CLOUDFLARE_ACCOUNT_ID", ""))
        self.cloudflare_token = tk.StringVar(value=os.getenv("CLOUDFLARE_API_TOKEN", ""))
        self.hf_token = tk.StringVar(value=os.getenv("HF_TOKEN", ""))
        self.gemini_key = tk.StringVar(value=os.getenv("GEMINI_API_KEY", ""))
        self.openai_key = tk.StringVar(value=os.getenv("OPENAI_API_KEY", ""))
        self.replicate_key = tk.StringVar(value=os.getenv("REPLICATE_API_TOKEN", ""))
        self.fal_key = tk.StringVar(value=os.getenv("FAL_KEY", ""))
        self.stability_key = tk.StringVar(value=os.getenv("STABILITY_API_KEY", ""))
        self.model_note = tk.StringVar(value=CATALOG[0].hint)
        self.status = tk.StringVar(value="Ready. Review every design before publishing.")

        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
        tabs = ttk.Notebook(self)
        tabs.pack(fill="both", expand=True, padx=12, pady=12)
        self.make_create_tab(tabs)
        self.make_queue_tab(tabs)
        self.make_trends_tab(tabs)
        self.make_settings_tab(tabs)
        ttk.Label(self, textvariable=self.status, anchor="w").pack(
            fill="x", padx=12, pady=(0, 10)
        )
        self.refresh_queue()
        self.after(100, self.poll_events)

    def make_create_tab(self, tabs: ttk.Notebook) -> None:
        tab = ttk.Frame(tabs, padding=18)
        tabs.add(tab, text="AI Design + SEO")
        ttk.Label(tab, text="Describe an ORIGINAL design (English usually works best)").pack(
            anchor="w"
        )
        self.prompt_widget = tk.Text(tab, height=8, wrap="word", undo=True)
        self.prompt_widget.pack(fill="x", pady=(5, 15))
        self.prompt_widget.insert(
            "1.0",
            "Minimalist mountain sunrise illustration, vintage ink style, clean centered "
            "composition for a t-shirt, no letters, no logos, no characters",
        )
        ttk.Label(tab, text="Niche / audience").pack(anchor="w")
        ttk.Entry(tab, textvariable=self.niche).pack(fill="x", pady=(4, 12))
        ttk.Label(tab, text="Relevant keywords (comma-separated; do not add trademarks)").pack(
            anchor="w"
        )
        ttk.Entry(tab, textvariable=self.keywords).pack(fill="x", pady=(4, 12))
        row = ttk.Frame(tab)
        row.pack(fill="x", pady=8)
        ttk.Label(row, text="Image provider:").pack(side="left", padx=(0, 5))
        ttk.Combobox(
            row, textvariable=self.provider_choice, state="readonly", width=40,
            values=[entry.label for entry in CATALOG],
        ).pack(side="left", padx=(0, 10))
        self.provider_choice.trace_add("write", self.update_model_note)
        ttk.Label(row, text="Gemini resolution:").pack(side="left", padx=(0, 5))
        ttk.Combobox(
            row, textvariable=self.gemini_size, state="readonly", width=5,
            values=["1K", "2K", "4K"],
        ).pack(side="left", padx=(0, 10))
        ttk.Label(row, text="SEO:").pack(side="left", padx=(0, 5))
        ttk.Combobox(
            row, textvariable=self.seo_choice, state="readonly", width=18,
            values=["Offline SEO", "Gemini AI SEO"],
        ).pack(side="left")
        ttk.Label(tab, textvariable=self.model_note, wraplength=820).pack(
            anchor="w", pady=(8, 0)
        )
        ttk.Label(
            tab, text="Paid image generation charges your provider account. "
            "PODBot never silently switches providers. Confirm cost before each call.",
            wraplength=820,
        ).pack(anchor="w")
        self.generate_button = ttk.Button(tab, text="Generate design + draft SEO", command=self.generate)
        self.generate_button.pack(anchor="w", pady=(15, 10))
        ttk.Button(
            tab, text="Import my PNG/JPEG/WebP (no AI fee)", command=self.import_local,
        ).pack(anchor="w", pady=(2, 10))
        ttk.Label(
            tab,
            text=("Creates one design per click. The print canvas is 5000 x 5500 px. "
                  "AI output may have an opaque background or insufficient detail. "
                  "Inspect before uploading."),
            wraplength=840,
        ).pack(anchor="w", pady=10)

    def make_queue_tab(self, tabs: ttk.Notebook) -> None:
        tab = ttk.Frame(tabs, padding=14)
        tabs.add(tab, text="Publishing Queue")
        self.tree = ttk.Treeview(
            tab, columns=("title", "redbubble", "teepublic"), show="headings", height=12
        )
        for name, width in [("title", 470), ("redbubble", 145), ("teepublic", 145)]:
            self.tree.heading(name, text=name.title())
            self.tree.column(name, width=width, stretch=name == "title")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.show_selected)
        actions = ttk.Frame(tab)
        actions.pack(fill="x", pady=10)
        ttk.Button(actions, text="Refresh", command=self.refresh_queue).pack(side="left", padx=3)
        ttk.Button(actions, text="Open PNG", command=self.open_selected).pack(side="left", padx=3)
        ttk.Button(actions, text="Preflight", command=self.preflight).pack(side="left", padx=3)
        ttk.Button(actions, text="Process PNG", command=self.process_selected).pack(side="left", padx=3)
        ttk.Button(actions, text="4 colors", command=self.preview_colors).pack(side="left", padx=3)
        ttk.Button(actions, text="Edit SEO", command=self.edit_seo).pack(side="left", padx=3)
        ttk.Button(actions, text="T-shirt mockup", command=self.create_mockup).pack(
            side="left", padx=3
        )
        ttk.Button(actions, text="Open Folder", command=self.open_folder).pack(side="left", padx=3)
        self.selected_platform = tk.StringVar(value="redbubble")
        ttk.Combobox(
            actions, textvariable=self.selected_platform, state="readonly", width=12,
            values=["redbubble", "teepublic"],
        ).pack(side="left", padx=5)
        ttk.Button(actions, text="Approve", command=lambda: self.set_state("approved")).pack(
            side="left", padx=3
        )
        ttk.Button(actions, text="Mark Uploaded", command=lambda: self.set_state("uploaded")).pack(
            side="left", padx=3
        )
        second = ttk.Frame(tab)
        second.pack(fill="x", pady=5)
        ttk.Button(second, text="Open platform upload page", command=self.open_upload).pack(
            side="left", padx=3
        )
        ttk.Button(second, text="Export queue to CSV", command=self.save_csv).pack(
            side="left", padx=3
        )
        ttk.Button(second, text="Edit Blocklist", command=self.edit_blocklist).pack(
            side="left", padx=3
        )
        self.details = tk.Text(tab, height=9, wrap="word")
        self.details.pack(fill="both", expand=True, pady=(12, 0))
        self.details.configure(state="disabled")

    def make_trends_tab(self, tabs: ttk.Notebook) -> None:
        tab = ttk.Frame(tabs, padding=16)
        tabs.add(tab, text="Trend Research")
        ttk.Label(tab, text="Google Trends RSS - discovery only, not approved product keywords").pack(anchor="w")
        controls = ttk.Frame(tab)
        controls.pack(anchor="w", pady=12)
        self.trend_country = tk.StringVar(value="US")
        ttk.Combobox(
            controls, state="readonly", width=8, textvariable=self.trend_country,
            values=["US", "GB", "CA", "AU", "DE", "FR", "JP", "KR", "BR", "IN"],
        ).pack(side="left", padx=(0, 12))
        self.trend_button = ttk.Button(
            controls, text="Fetch public trends", command=self.fetch_trends,
        )
        self.trend_button.pack(side="left")
        self.trend_list = tk.Listbox(tab, height=17)
        self.trend_list.pack(fill="both", expand=True)
        ttk.Button(
            tab, text="Copy selected trend (review trademarks before use)",
            command=self.copy_trend,
        ).pack(anchor="w", pady=12)
        ttk.Label(
            tab,
            text=("Source: trends.google.com/trending/rss. Data is unfiltered popularity, "
                  "not a POD opportunity score. Brand names, people, shows, and copyrighted "
                  "terms require separate legal review. No unattended scraping."),
            wraplength=800,
        ).pack(anchor="w")

    def fetch_trends(self) -> None:
        country = self.trend_country.get()
        self.trend_button.configure(state="disabled")
        self.status.set("Reading Google Trends RSS on demand...")

        def worker() -> None:
            try:
                trends = read_trends(country, limit=15)
                self.events.put(("trends", trends))
            except (OSError, RuntimeError, ValueError) as exc:
                self.events.put(("trends_error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def copy_trend(self) -> None:
        selected = self.trend_list.curselection()
        if not selected:
            messagebox.showinfo("Choose trend", "Select one item from the trend list.")
            return
        title = self.trend_list.get(selected[0]).split(" | ", 1)[0]
        self.clipboard_clear()
        self.clipboard_append(title)
        self.status.set("Copied a research topic. Review IP before designing.")

    def update_model_note(self, *_args) -> None:
        selected = LABELS.get(self.provider_choice.get())
        if selected:
            spec = get_spec(selected)
            self.model_note.set(spec.hint + " | Key: " + spec.env_key)

    def make_settings_tab(self, tabs: ttk.Notebook) -> None:
        tab = ttk.Frame(tabs, padding=20)
        tabs.add(tab, text="API Settings")
        for label, variable, secret in [
            ("Cloudflare Account ID", self.account_id, False),
            ("Cloudflare API token", self.cloudflare_token, True),
            ("Hugging Face token", self.hf_token, True),
            ("Gemini API key (image + SEO)", self.gemini_key, True),
            ("OpenAI API key (image generation)", self.openai_key, True),
            ("Replicate API token", self.replicate_key, True),
            ("fal.ai API key", self.fal_key, True),
            ("Stability API key", self.stability_key, True),
        ]:
            ttk.Label(tab, text=label).pack(anchor="w", pady=(10, 2))
            ttk.Entry(tab, textvariable=variable, show="*" if secret else "").pack(fill="x")
        ttk.Label(
            tab,
            text=("Keys stay in process memory and are NEVER written to settings or project files. "
                  "Use environment variables as an alternative. Each billed model requires "
                  "a separate confirmation. Free-tier credits can be exhausted."),
            wraplength=700,
        ).pack(anchor="w", pady=22)
        ttk.Button(
            tab, text="Open local data folder",
            command=lambda: webbrowser.open(data_directory().as_uri()),
        ).pack(anchor="w")
        ttk.Label(tab, text="No account passwords, browser sessions or cookies are collected.").pack(
            anchor="w", pady=16
        )

    def import_local(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose your own design (no image API request)",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp")],
        )
        if not path:
            return
        niche, keywords = self.niche.get(), self.keywords.get()
        self.status.set("Importing local artwork, no image API charges...")

        def worker() -> None:
            try:
                saved = import_design(Path(path), niche, keywords)
                self.events.put(("success", saved))
            except (OSError, ValueError, RuntimeError) as exc:
                self.events.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def generate(self) -> None:
        prompt = self.prompt_widget.get("1.0", "end").strip()
        if len(prompt) < 5:
            messagebox.showerror("Prompt required", "Enter at least 5 characters.")
            return
        if not messagebox.askyesno(
            "Rights check", "Confirm you have rights to the concept and reviewed it for "
            "trademarks, copyrighted characters and sensitive claims?",
        ):
            return
        model_id = LABELS.get(self.provider_choice.get())
        if not model_id:
            messagebox.showerror("Image model", "Choose a supported image model.")
            return
        spec = get_spec(model_id)
        mode = "gemini" if self.seo_choice.get() == "Gemini AI SEO" else "local"
        if (spec.paid or mode == "gemini") and not messagebox.askyesno(
            "Confirm paid API request",
            "Selected model: " + spec.label + "\n\n" + spec.hint
            + "\n\nGemini SEO: " + ("ON" if mode == "gemini" else "OFF")
            + "\nThis may consume paid credits, potentially twice for image + SEO. "
              "Costs depend on provider settings and current pricing.\n"
              "Proceed with exactly ONE generation request, no paid fallback?",
        ):
            return
        credentials = {
            "CLOUDFLARE_ACCOUNT_ID": self.account_id.get(),
            "CLOUDFLARE_API_TOKEN": self.cloudflare_token.get(),
            "HF_TOKEN": self.hf_token.get(),
            "GEMINI_API_KEY": self.gemini_key.get(),
            "OPENAI_API_KEY": self.openai_key.get(),
            "REPLICATE_API_TOKEN": self.replicate_key.get(),
            "FAL_KEY": self.fal_key.get(),
            "STABILITY_API_KEY": self.stability_key.get(),
        }
        try:
            provider = make_provider(
                model_id, credentials, allow_paid=spec.paid,
                gemini_size=self.gemini_size.get(),
            )
        except (ValueError, PermissionError) as exc:
            messagebox.showerror("Image provider", str(exc))
            return
        niche, keywords, key = self.niche.get(), self.keywords.get(), self.gemini_key.get()
        if matches := find_blocked_terms(f"{prompt} {niche} {keywords}", get_blocklist()):
            messagebox.showerror("Blocklist", "Review these terms: " + ", ".join(matches))
            return
        self.generate_button.configure(state="disabled")
        self.status.set("Generating... Your desktop remains responsive.")

        def worker() -> None:
            try:
                record = create_draft(prompt, niche, keywords, provider, mode, key)
                self.events.put(("success", record))
            except Exception as exc:  # noqa: BLE001
                self.events.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def poll_events(self) -> None:
        try:
            while True:
                kind, result = self.events.get_nowait()
                if kind in {"trends", "trends_error"}:
                    self.trend_button.configure(state="normal")
                    if kind == "trends":
                        self.trend_list.delete(0, "end")
                        for trend in result:
                            self.trend_list.insert(
                                "end",
                                f"{trend.title} | {trend.approx_traffic} | {trend.published}",
                            )
                        self.status.set(
                            f"Loaded {len(result)} attributed trends. Review each concept."
                        )
                    else:
                        self.status.set("Trend RSS unavailable.")
                        messagebox.showerror("Trend research error", str(result))
                    continue
                if kind in {"processed", "approved", "uploaded", "studio_error"}:
                    if kind == "studio_error":
                        messagebox.showerror("Studio workflow", str(result))
                    else:
                        self.refresh_queue()
                        self.status.set("Local draft / review record updated.")
                        if kind == "processed":
                            messagebox.showinfo(
                                "New print PNG", "Reprocessed from original. Approval reset.",
                            )
                    continue
                self.generate_button.configure(state="normal")
                if kind == "success":
                    self.refresh_queue()
                    self.status.set("Draft generated. Review print quality and SEO before upload.")
                    record = result
                    messagebox.showinfo(
                        "Draft ready",
                        f"Design saved to:\n{Path(record['print_file']).parent}\n\n"
                        f"Quality note: {record['quality_warning']}",
                    )
                else:
                    self.status.set("Generation failed. No partial draft was added to the queue.")
                    messagebox.showerror("Generation error", str(result))
        except queue.Empty:
            pass
        self.after(100, self.poll_events)

    def refresh_queue(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.records = {r["id"]: r for r in list_designs()}
        for item in self.records.values():
            self.tree.insert(
                "", "end", iid=item["id"],
                values=(
                    item["seo"]["title"],
                    item["platform_status"].get("redbubble", "draft"),
                    item["platform_status"].get("teepublic", "draft"),
                ),
            )
        self.status.set(f"{len(self.records)} design drafts stored locally.")

    def selected(self) -> dict | None:
        ids = self.tree.selection()
        if not ids:
            messagebox.showinfo("Select design", "Select a design from the queue first.")
            return None
        return self.records[ids[0]]

    def show_selected(self, _event=None) -> None:
        ids = self.tree.selection()
        if not ids:
            return
        item = self.records[ids[0]]
        seo = item["seo"]
        summary = (
            f"TITLE: {seo['title']}\n\nDESCRIPTION: {seo['description']}\n\n"
            f"TAGS: {', '.join(seo['tags'])}\n\n"
            f"QUALITY: {item['quality_warning']}\n"
        )
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", summary)
        self.details.configure(state="disabled")

    def open_selected(self) -> None:
        item = self.selected()
        if item:
            webbrowser.open(Path(item["print_file"]).as_uri())

    def open_folder(self) -> None:
        item = self.selected()
        if item:
            folder = Path(item["print_file"]).parent
            if os.name == "nt":
                os.startfile(folder)  # native Windows file viewer
            else:
                webbrowser.open(folder.as_uri())

    def preflight(self) -> None:
        item = self.selected()
        if not item:
            return
        platform = self.selected_platform.get()
        try:
            with Image.open(item["print_file"]) as asset:
                checks = audit_image(asset, platform)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Preflight error", str(exc))
            return
        summary = "\\n".join(
            f"{check.level.upper()} | {check.name}: {check.value} | {check.message}"
            for check in checks
        )
        matched = near_duplicates(item, list(self.records.values()))
        if matched:
            summary += "\nWARN | Similar local design IDs: " + ", ".join(matched[:5])
        messagebox.showinfo(
            f"Print / QC: {platform}",
            summary + "\\n\\nEvery FAIL blocks approval. Warnings require human review.",
        )

    def create_mockup(self) -> None:
        item = self.selected()
        if not item:
            return
        source = Path(item["print_file"])
        target = source.parent / "mockup-shirt.png"
        try:
            with Image.open(source) as image:
                create_shirt_mockup(image, target)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Mockup error", str(exc))
            return
        webbrowser.open(target.as_uri())
        self.status.set("Illustrative T-shirt mockup created locally.")

    def edit_seo(self) -> None:
        item = self.selected()
        if not item:
            return
        metadata = item["seo"]
        popup = tk.Toplevel(self)
        popup.title("Edit SEO draft")
        popup.geometry("730x510")
        popup.transient(self)
        popup.grab_set()
        frame = ttk.Frame(popup, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Title (80 characters maximum)").pack(anchor="w")
        title = tk.StringVar(value=metadata["title"])
        ttk.Entry(frame, textvariable=title).pack(fill="x", pady=5)
        ttk.Label(frame, text="Description (700 characters maximum)").pack(anchor="w")
        description = tk.Text(frame, height=8, wrap="word")
        description.pack(fill="both", expand=True, pady=5)
        description.insert("1.0", metadata["description"])
        ttk.Label(frame, text="Tags (comma-separated; 15 maximum)").pack(anchor="w")
        tags = tk.Text(frame, height=4, wrap="word")
        tags.pack(fill="x", pady=5)
        tags.insert("1.0", ", ".join(metadata["tags"]))

        def save() -> None:
            try:
                update_seo(
                    item["id"], title.get(),
                    description.get("1.0", "end").strip(),
                    tags.get("1.0", "end").split(","),
                )
            except (OSError, ValueError) as exc:
                messagebox.showerror("SEO could not be saved", str(exc), parent=popup)
                return
            popup.destroy()
            self.refresh_queue()
            self.tree.selection_set(item["id"])
            self.show_selected()
            self.status.set("Saved manually reviewed SEO metadata.")

        ttk.Button(frame, text="Save metadata", command=save).pack(anchor="e", pady=12)

    def edit_blocklist(self) -> None:
        path = data_directory() / "blocklist.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(
                "# User-maintained risk terms; one phrase per line. Not a trademark registry.\n",
                encoding="utf-8",
            )
        if os.name == "nt":
            os.startfile(path)
        else:
            webbrowser.open(path.as_uri())

    def preview_colors(self) -> None:
        item = self.selected()
        if not item:
            return
        target = Path(item["print_file"]).parent / "preview-4-colors.png"
        try:
            with Image.open(item["print_file"]) as original:
                thumbnail = original.copy()
                thumbnail.thumbnail((1000, 1000))
                make_color_preview(thumbnail, target)
            webbrowser.open(target.as_uri())
        except (OSError, ValueError) as exc:
            messagebox.showerror("Preview", str(exc))

    def process_selected(self) -> None:
        item = self.selected()
        if not item:
            return
        use_bg = messagebox.askyesno(
            "Optional background removal",
            "Use a separately installed rembg executable? It may download its model "
            "on first run. No models are included in PODBot.exe. Choose No to crop only.",
        )
        rembg_binary = None
        if use_bg:
            path = filedialog.askopenfilename(
                title="Select installed rembg.exe",
                filetypes=[("Executable", "*.exe"), ("All files", "*")],
            )
            if not path:
                return
            rembg_binary = Path(path)
        use_sr = messagebox.askyesno(
            "Optional AI upscale",
            "Use an external realesrgan-ncnn-vulkan.exe, separately downloaded by you? "
            "Choose No for ordinary Lanczos scaling.",
        )
        sr_binary = None
        if use_sr:
            path = filedialog.askopenfilename(
                title="Select Real-ESRGAN executable",
                filetypes=[("Executable", "*.exe"), ("All files", "*")],
            )
            if not path:
                return
            sr_binary = Path(path)
        if not messagebox.askyesno(
            "Rebuild print asset",
            "Rebuild from original source? This creates a new PNG and invalidates "
            "both platform approvals. Review output and rights before approval.",
        ):
            return
        options = ProcessOptions(
            remove_background=use_bg, rembg_binary=rembg_binary,
            upscale=use_sr, esrgan_binary=sr_binary,
        )
        design_id = item["id"]
        self.status.set("Image processor working in background...")

        def worker() -> None:
            try:
                saved = process_stored_design(design_id, options)
                self.events.put(("processed", saved))
            except (OSError, ValueError, RuntimeError) as exc:
                self.events.put(("studio_error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def set_state(self, state: str) -> None:
        item = self.selected()
        if not item:
            return
        platform = self.selected_platform.get()
        if state == "approved":
            if not item.get("rights_confirmed_at"):
                if not messagebox.askyesno(
                    "Commercial rights confirmation",
                    "I confirm I own or hold commercial rights to the artwork, have checked "
                    "trademarks, current marketplace rules and all listing metadata.",
                ):
                    return
                confirm_rights(item["id"])
            self.status.set("Running quality and publishing checks...")
        else:
            if item.get("platform_status", {}).get(platform) != "approved":
                messagebox.showerror("Cannot upload", "Approve this design first.")
                return
            if not messagebox.askyesno(
                "Manual upload confirmation",
                "Have you personally uploaded this exact design and checked it in "
                "your seller dashboard?",
            ):
                return
        design_id = item["id"]

        def worker() -> None:
            try:
                record = (
                    approve_listing(design_id, platform) if state == "approved"
                    else mark_uploaded(design_id, platform, confirmed=True)
                )
                self.events.put((state, record))
            except (OSError, ValueError, RuntimeError) as exc:
                self.events.put(("studio_error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def open_upload(self) -> None:
        item = self.selected()
        if not item:
            return
        platform = self.selected_platform.get()
        if item.get("platform_status", {}).get(platform) != "approved":
            messagebox.showerror(
                "Approval required",
                "Only an approved design may enter the manual upload workflow.",
            )
            return
        messagebox.showinfo(
            "Manual publishing only",
            "First review the official platform rules. Upload your PNG manually, "
            "verify product placement, art and SEO, then confirm Uploaded in PODBot. "
            "No passwords, browser scripts, or CAPTCHA automation are used.",
        )
        webbrowser.open(POLICY_URLS[platform])
        webbrowser.open(UPLOAD_PAGES[platform])

    def save_csv(self) -> None:
        platform = self.selected_platform.get()
        target = filedialog.asksaveasfilename(
            title="Export metadata for manual review",
            defaultextension=".csv", filetypes=[("CSV files", "*.csv")],
            initialfile=f"podbot-{platform}-queue.csv",
        )
        if target:
            count = export_csv(Path(target), platform)
            messagebox.showinfo("Queue exported", f"Saved {count} records.")


def main() -> None:
    PODBotApp().mainloop()


if __name__ == "__main__":
    main()
