"""Headless GUI contract tests: no window or network is created."""

import sys
from pathlib import Path

import pytest

from podbot.modern_app import (
    ACCENT,
    MENU,
    STATUSES,
    TEXT,
    PODBotDesktop,
    model_options,
    status_label,
)
from podbot.provider_catalog import CATALOG


def test_vietnamese_is_default_ui_language():
    assert TEXT["language"] == "Tiếng Việt"
    assert "Tạo thiết kế" in TEXT["create"]
    assert "Bản nháp" in TEXT["status_draft"]
    assert status_label("approved") == "Đã duyệt"
    assert STATUSES["uploaded"] == "Đã đăng"


def test_navigation_has_five_vietnamese_sections():
    assert [key for key, _ in MENU] == [
        "overview", "create", "library", "trends", "settings"
    ]
    assert any("Thư viện" in label for _, label in MENU)
    assert any("Cài đặt" in label for _, label in MENU)
    assert len({label for _, label in MENU}) == len(MENU)


def test_model_selection_has_every_supported_provider():
    assert model_options() == [spec.label for spec in CATALOG]
    assert len(model_options()) >= 14
    assert len(set(model_options())) == len(model_options())


def test_design_uses_independent_sidebar_and_pod_workflow():
    assert ACCENT.startswith("#")
    assert callable(PODBotDesktop.generate)
    assert callable(PODBotDesktop.import_file)
    assert callable(PODBotDesktop.approve)
    assert callable(PODBotDesktop.preflight)
    assert callable(PODBotDesktop.preview_shirt)
    assert callable(PODBotDesktop.mark_uploaded)
    assert callable(PODBotDesktop.edit_seo)


def test_single_exe_build_collects_customtkinter_assets():
    root = Path(__file__).resolve().parents[1]
    github_workflow = (root / ".github/workflows/windows-build.yml").read_text(encoding="utf-8")
    powershell = (root / "scripts/build_windows.ps1").read_text(encoding="utf-8")
    assert "--onefile" in github_workflow
    assert "--collect-all customtkinter" in github_workflow
    assert "--collect-all customtkinter" in powershell


def test_entrypoint_launches_vietnamese_studio():
    from podbot.app import PODBotApp, main

    assert PODBotApp is PODBotDesktop
    assert main.__module__ == "podbot.modern_app"


@pytest.mark.skipif(sys.platform != "win32", reason="Requires native Windows Tk GUI")
def test_real_windows_ui_starts_with_free_catalog_auto_refresh_disabled(monkeypatch):
    """An actual Tk variable, not a source-text pattern, guards network privacy."""
    from podbot import modern_app

    class NoDiskQueue:
        def recover(self):
            return None

    monkeypatch.setattr(modern_app, "JobQueue", NoDiskQueue)
    monkeypatch.setattr(modern_app, "list_designs", list)
    monkeypatch.setattr(modern_app, "get_daily_limit", lambda: 0)
    monkeypatch.setattr(
        modern_app, "refresh_public_catalog",
        lambda **_kwargs: pytest.fail("Catalog network must be opt-in"),
    )
    app = modern_app.PODBotDesktop()
    try:
        app.withdraw()
        assert app.free_catalog_autoupdate.get() is False
        app.show_page("settings")
        assert app.free_catalog_autoupdate.get() is False
    finally:
        app.destroy()
