"""Release scripts must not publish untested Windows executables."""

from pathlib import Path


def test_release_validates_both_windows_formats_before_publishing():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github/workflows/release-windows.yml").read_text(
        encoding="utf-8"
    )
    onedir = workflow.index("Verify native onedir EXE and GUI before release")
    onefile = workflow.index("Verify native onefile EXE before release")
    publish = workflow.index("softprops/action-gh-release")
    assert onedir < onefile < publish
    assert "Release onedir smoke failed" in workflow
    assert "Release onefile smoke failed" in workflow
    assert "Release GUI stopped unexpectedly" in workflow
    assert "--smoke-test" in workflow
    assert "--require-hashes -r requirements/windows-py312.lock.txt" in workflow
    assert "python -m pip_audit --local" in workflow
    assert "python -m ruff check src tests scripts" in workflow


def test_paid_api_workflow_remains_manual_and_opt_in():
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github/workflows/paid-api-manual.yml").read_text(
        encoding="utf-8"
    )
    assert "workflow_dispatch:" in workflow
    assert "if: inputs.confirmation == 'YES_I_ACCEPT_POTENTIAL_CHARGES'" in workflow
    assert "${{ secrets.OPENAI_API_KEY }}" in workflow
    assert "PODBOT_PAID_CALLS_PER_DAY: \"1\"" in workflow
    assert "contents: read" in workflow
