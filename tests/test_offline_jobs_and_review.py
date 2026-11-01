"""Offline queue, real-world edge proxies and no-network OCR tests."""

import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFilter

from podbot.image_review import create_fabric_preview, inspect_halo, scan_ocr
from podbot.job_queue import JobQueue


def test_queue_survives_reopen_recovery_and_retry(tmp_path):
    filename = tmp_path / "jobs.sqlite3"
    first = JobQueue(filename)
    job = first.enqueue("reprocess", {"design_id": "a" * 32, "flat_background": True})
    assert first.claim().id == job.id
    second = JobQueue(filename)
    assert second.recover() == 1
    claimed = second.claim()
    assert claimed.status == "running" and claimed.attempts == 2
    second.finish(job.id, error="provider-secret-would-be-redacted")
    assert second.list()[0].error == "Task failed; inspect local logs without credentials."
    assert second.retry(job.id)
    assert second.claim().attempts == 3
    second.finish(job.id)
    assert second.list()[0].status == "succeeded"
    assert not second.retry(job.id)


def test_queue_cancel_pending_and_no_billed_jobs(tmp_path):
    queue = JobQueue(tmp_path / "queue.db")
    with pytest.raises(ValueError):
        queue.enqueue("generate", {"design_id": "a" * 32, "OPENAI_API_KEY": "secret"})
    with pytest.raises(ValueError):
        queue.enqueue("reprocess", {"design_id": "../secrets", "flat_background": True})
    with pytest.raises(ValueError):
        queue.enqueue("reprocess", {"design_id": "b" * 32, "flat_background": True,
                                     "token": "secret"})
    item = queue.enqueue("inspect", {"design_id": "b" * 32, "platform": "teepublic"})
    assert queue.cancel(item.id)
    assert queue.claim() is None
    assert not queue.cancel(item.id)


def test_queue_interrupted_last_attempt_does_not_loop(tmp_path):
    queue = JobQueue(tmp_path / "jobs.db")
    item = queue.enqueue("inspect", {"design_id": "b" * 32, "platform": "redbubble"},
                         max_attempts=1)
    assert queue.claim().attempts == 1
    assert queue.recover() == 1
    assert queue.list()[0].status == "failed"
    assert queue.claim() is None
    assert not queue.retry(item.id)


def test_halo_inspection_and_realistic_offwhite_shadow(tmp_path):
    img = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    layer = Image.new("RGBA", img.size)
    ImageDraw.Draw(layer).ellipse((50, 40, 250, 260), fill=(25, 45, 85, 255))
    mask = layer.getchannel("A").filter(ImageFilter.GaussianBlur(1.5))
    layer.putalpha(mask)
    img.alpha_composite(layer)
    assert not inspect_halo(img).warning
    halo = Image.new("RGBA", (300, 300), (255, 255, 255, 0))
    matte = Image.new("L", (300, 300))
    ImageDraw.Draw(matte).ellipse((50, 40, 250, 260), fill=255)
    halo.putalpha(matte.filter(ImageFilter.GaussianBlur(2)))
    assert inspect_halo(halo).warning
    result = create_fabric_preview(img, tmp_path / "three-shirts.png")
    with Image.open(result) as preview:
        assert preview.width == 1560 and preview.height == 520


def test_optional_ocr_fails_closed_without_program(monkeypatch):
    monkeypatch.setattr("podbot.image_review.shutil.which", lambda _: None)
    result = scan_ocr(Image.new("RGB", (140, 140), "white"))
    assert result.available is False
    assert result.text == ""


def test_optional_ocr_uses_local_executable_and_no_shell(monkeypatch, tmp_path):
    captures = []

    def fake_run(args, **kwargs):
        captures.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, b"ORIGINAL DESIGN\n", b"")

    monkeypatch.setattr("podbot.image_review.shutil.which", lambda path: "/fake/tesseract")
    monkeypatch.setattr("podbot.image_review.subprocess.run", fake_run)
    output = scan_ocr(Image.new("RGB", (140, 140), "white"))
    assert output.available and output.text == "ORIGINAL DESIGN"
    assert captures[0][0][-3:] == ["stdout", "-l", "eng"]
    assert captures[0][1]["shell"] is False
    with pytest.raises(ValueError):
        scan_ocr(Image.new("RGB", (140, 140)), language="arbitrary")
