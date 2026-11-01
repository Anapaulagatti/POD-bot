"""Windows application entry point: Vietnamese modern desktop by default."""

from podbot.modern_app import PODBotDesktop, main

PODBotApp = PODBotDesktop


def smoke_test() -> None:
    """Read-only packaging test that never opens a window or calls a paid API."""
    from pathlib import Path
    from tempfile import TemporaryDirectory

    from PIL import Image, ImageDraw

    from podbot.flat_background import remove_flat_background
    from podbot.image_review import inspect_halo
    from podbot.job_queue import JobQueue

    with TemporaryDirectory(prefix="podbot-smoke-") as temp:
        picture = Image.new("RGB", (160, 160), "white")
        ImageDraw.Draw(picture).ellipse((35, 35, 125, 125), fill=(25, 40, 75))
        result = remove_flat_background(picture)
        if result.getpixel((0, 0))[3] or inspect_halo(result).warning:
            raise RuntimeError("Bundled image processing failed.")
        jobs = JobQueue(Path(temp) / "jobs.sqlite3")
        job = jobs.enqueue("inspect", {"design_id": "a" * 32, "platform": "redbubble"})
        if not jobs.cancel(job.id):
            raise RuntimeError("Bundled SQLite queue failed.")


if __name__ == "__main__":
    import sys

    if "--smoke-test" in sys.argv:
        smoke_test()
    else:
        main()
