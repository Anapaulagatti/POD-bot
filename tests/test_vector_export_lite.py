"""Optional VTracer CPU vector export must be bounded, safe, and review-only."""

import json
from pathlib import Path

import pytest
from PIL import Image

from podbot.storage import save_manifest
from podbot.vector_export import export_vector

SVG = '<svg xmlns="http://www.w3.org/2000/svg"><path d="M 1 2 L 3 4"/></svg>'


def setup_design(tmp_path):
    identifier = "a" * 32
    folder = tmp_path / identifier
    folder.mkdir()
    Image.new("RGBA", (2100, 1800), (50, 75, 120, 255)).save(folder / "source.png")
    original = {
        "id": identifier,
        "platform_status": {"redbubble": "approved", "teepublic": "draft"},
        "approval_evidence": {"redbubble": {"operator": "reviewed"}},
    }
    save_manifest(folder, original)
    tool = tmp_path / "vtracer.exe"
    tool.write_bytes(b"test exe")
    return identifier, folder, original, tool


def test_vectorize_cpu_caps_input_and_does_not_change_manifest(monkeypatch, tmp_path):
    identifier, folder, record, tool = setup_design(tmp_path)
    before = (folder / "manifest.json").read_bytes()
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        with Image.open(argv[1]) as source:
            assert max(source.size) == 1600
        Path(argv[2]).write_text(SVG, encoding="utf-8")
        return type("Result", (), {"returncode": 0})()

    monkeypatch.setattr("podbot.vector_export.subprocess.run", fake_run)
    output = export_vector(identifier, tool, root=tmp_path, max_colors=4)
    assert output.suffix == ".svg"
    assert output.parent == folder
    assert output.read_text() == SVG
    assert (folder / "manifest.json").read_bytes() == before
    argv, kwargs = calls[0]
    assert argv[-4:] == ["--max-colors", "4", "--filter-speckle", "4"]
    assert kwargs["shell"] is False
    assert kwargs["timeout"] == 180


@pytest.mark.parametrize("payload", [
    '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><image href="https://evil.test"/></svg>',
    '<svg xmlns="http://www.w3.org/2000/svg"><path onload="x()" d="M 0 0"/></svg>',
    '<!DOCTYPE svg [ <!ENTITY x "y"> ]><svg xmlns="http://www.w3.org/2000/svg"/>',
])
def test_vector_export_rejects_svg_active_content(monkeypatch, tmp_path, payload):
    identifier, folder, _, tool = setup_design(tmp_path)
    def fake_run(argv, **kwargs):
        Path(argv[2]).write_text(payload, encoding="utf-8")
        return type("Result", (), {"returncode": 0})()
    monkeypatch.setattr("podbot.vector_export.subprocess.run", fake_run)
    with pytest.raises(RuntimeError):
        export_vector(identifier, tool, root=tmp_path)
    assert not list(folder.glob("vector_preview_*.svg"))


def test_invalid_config_fails_before_executing_tool(monkeypatch, tmp_path):
    identifier, folder, _, tool = setup_design(tmp_path)
    monkeypatch.setattr("podbot.vector_export.subprocess.run",
                        lambda *_args, **_kwargs: pytest.fail("untrusted executable"))
    for kwargs in ({"max_colors": 8}, {"max_colors": 1}, {"max_colors": True}):
        with pytest.raises(ValueError):
            export_vector(identifier, tool, root=tmp_path, **kwargs)
    with pytest.raises(ValueError):
        export_vector("../unsafe", tool, root=tmp_path)
    with pytest.raises(ValueError, match="installed"):
        export_vector(identifier, tmp_path / "missing.exe", root=tmp_path)


def test_failed_cli_keeps_existing_pod_assets(monkeypatch, tmp_path):
    identifier, folder, original, tool = setup_design(tmp_path)
    source_bytes = (folder / "source.png").read_bytes()
    monkeypatch.setattr(
        "podbot.vector_export.subprocess.run",
        lambda *_args, **_kwargs: type("Result", (), {"returncode": 2})(),
    )
    with pytest.raises(RuntimeError, match="CLI rejected"):
        export_vector(identifier, tool, root=tmp_path)
    assert (folder / "source.png").read_bytes() == source_bytes
    assert json.loads((folder / "manifest.json").read_text()) == original
