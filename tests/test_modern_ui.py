"""Headless GUI contract tests: no window or network is created."""

from pathlib import Path

from podbot.modern_app import (
    ACCENT,
    MENU,
    PODBotDesktop,
    STATUSES,
    TEXT,
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
