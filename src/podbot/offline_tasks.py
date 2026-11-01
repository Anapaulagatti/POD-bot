"""Safe task dispatcher for crash-recoverable offline jobs; no paid providers."""

from __future__ import annotations

from PIL import Image

from podbot.audit import audit_image, get_blocklist
from podbot.image_review import inspect_halo, review_ocr, scan_ocr
from podbot.job_queue import JobQueue
from podbot.processing import ProcessOptions, process_stored_design
from podbot.storage import list_designs


def execute_next(queue: JobQueue):
    """Execute exactly one queued offline task and record its terminal state."""
    job = queue.claim()
    if job is None:
        return None
    try:
        if job.kind == "reprocess":
            result = process_stored_design(
                job.payload["design_id"],
                ProcessOptions(flat_background=job.payload["flat_background"]),
            )
        elif job.kind == "inspect":
            entry = next(
                (x for x in list_designs() if x["id"] == job.payload["design_id"]),
                None,
            )
            if entry is None:
                raise ValueError("Design not found.")
            with Image.open(entry["print_file"]) as art:
                checks = audit_image(art, job.payload["platform"])
                halo = inspect_halo(art)
                ocr = scan_ocr(art)
                checks.extend(review_ocr(ocr, get_blocklist(), prompt=entry.get("prompt", "")))
            lines = [f"{x.level.upper()} · {x.name} · {x.message}" for x in checks]
            lines.append(
                f"Viền sáng: {halo.bright_share:.1%} "
                f"({halo.bright_partial_pixels}/{halo.partial_pixels} pixel bán trong suốt)"
            )
            if halo.warning:
                lines.append("CẢNH BÁO: Cần xem ảnh trên nền áo tối và sáng.")
            lines.append(
                f"OCR: {ocr.text if ocr.available else ocr.note}"
            )
            result = {"_job_inspection": "\n".join(lines)}
        else:
            raise ValueError("Unsupported task type.")
    except Exception as exc:
        queue.finish(job.id, error=str(exc))
        raise
    queue.finish(job.id)
    return result
