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

from podbot.mockups import create_shirt_mockup
from podbot.pipeline import create_draft
from podbot.quality import assess_design
from podbot.trends import read_trends
from podbot.providers import CloudflareFluxProvider, HuggingFaceProvider
from podbot.settings import data_directory
from podbot.storage import export_csv, list_designs, update_state

UPLOAD_PAGES = {
    "redbubble": "https://www.redbubble.com/portfolio/images/new",
    "teepublic": "https://www.teepublic.com/",
}


class PODBotApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PODBot Studio v0.1 | Local-first")
        self.geometry("980x720")
        self.minsize(780, 600)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.records: dict[str, dict] = {}
        self.provider_choice = tk.StringVar(value="Cloudflare FLUX")
        self.seo_choice = tk.StringVar(value="Offline SEO")
        self.niche = tk.StringVar(value="minimalist nature")
        self.keywords = tk.StringVar(value="mountain silhouette, hiking, adventure")
        self.account_id = tk.StringVar(value=os.getenv("CLOUDFLARE_ACCOUNT_ID", ""))
        self.cloudflare_token = tk.StringVar(value=os.getenv("CLOUDFLARE_API_TOKEN", ""))
        self.hf_token = tk.StringVar(value=os.getenv("HF_TOKEN", ""))
        self.gemini_key = tk.StringVar(value=os.getenv("GEMINI_API_KEY", ""))
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
            row, textvariable=self.provider_choice, state="readonly", width=22,
            values=["Cloudflare FLUX", "Hugging Face"],
        ).pack(side="left", padx=(0, 20))
        ttk.Label(row, text="SEO:").pack(side="left", padx=(0, 5))
        ttk.Combobox(
            row, textvariable=self.seo_choice, state="readonly", width=18,
            values=["Offline SEO", "Gemini AI SEO"],
        ).pack(side="left")
        self.generate_button = ttk.Button(tab, text="Generate design + draft SEO", command=self.generate)
        self.generate_button.pack(anchor="w", pady=(15, 10))
        ttk.Label(
            tab,
            text=("Creates one design per click. The print canvas is 4500 x 5400 px. "
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

    def make_settings_tab(self, tabs: ttk.Notebook) -> None:
        tab = ttk.Frame(tabs, padding=20)
        tabs.add(tab, text="API Settings")
        for label, variable, secret in [
            ("Cloudflare Account ID", self.account_id, False),
            ("Cloudflare API token", self.cloudflare_token, True),
            ("Hugging Face token", self.hf_token, True),
            ("Gemini API key (optional SEO)", self.gemini_key, True),
        ]:
            ttk.Label(tab, text=label).pack(anchor="w", pady=(10, 2))
            ttk.Entry(tab, textvariable=variable, show="*" if secret else "").pack(fill="x")
        ttk.Label(
            tab,
            text=("Keys stay in process memory and are NEVER written to project files "
                  "or saved settings. You may set environment variables instead. "
                  "API providers have rate limits and may require billing configuration."),
            wraplength=700,
        ).pack(anchor="w", pady=22)
        ttk.Button(
            tab, text="Open local data folder",
            command=lambda: webbrowser.open(data_directory().as_uri()),
        ).pack(anchor="w")
        ttk.Label(tab, text="No account passwords, browser sessions or cookies are collected.").pack(
            anchor="w", pady=16
        )

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
        provider_name = self.provider_choice.get()
        provider = (
            CloudflareFluxProvider(self.account_id.get().strip(), self.cloudflare_token.get())
            if provider_name == "Cloudflare FLUX" else HuggingFaceProvider(self.hf_token.get())
        )
        mode = "gemini" if self.seo_choice.get() == "Gemini AI SEO" else "local"
        niche, keywords, key = self.niche.get(), self.keywords.get(), self.gemini_key.get()
        self.generate_button.configure(state="disabled")
        self.status.set("Generating... Your desktop remains responsive.")

        def worker() -> None:
            try:
                record = create_draft(prompt, niche, keywords, provider, mode, key)
                self.events.put(("success", record))
            except Exception as exc:  # noqa: BLE001; show errors in UI worker
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
            report = assess_design(item, platform)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Preflight error", str(exc))
            return
        notes = "\\n".join(report.issues) if report.issues else "No automatic warnings detected."
        messagebox.showinfo(
            f"Print preflight: {platform}",
            f"Canvas: {report.canvas_size[0]} x {report.canvas_size[1]}\\n"
            f"Artwork: {report.artwork_size[0]} x {report.artwork_size[1]}\\n\\n"
            f"{notes}\\n\\nAutomated checks cannot guarantee print quality or IP clearance.",
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

    def set_state(self, state: str) -> None:
        item = self.selected()
        if not item:
            return
        platform = self.selected_platform.get()
        if state == "uploaded" and not messagebox.askyesno(
            "Manual confirmation", f"Did you PERSONALLY upload this design to {platform}?",
        ):
            return
        update_state(item["id"], platform, state)
        self.refresh_queue()

    def open_upload(self) -> None:
        platform = self.selected_platform.get()
        messagebox.showinfo(
            "Manual publishing only",
            "This opens the platform in your browser. PODBot does not use unapproved "
            "automation, submit uploads, handle CAPTCHA, or store login credentials.",
        )
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
