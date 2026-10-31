"""Explicit local image process: optional external rembg -> ESRGAN -> cutout canvas.

External binaries/models are NEVER bundled or downloaded automatically.
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps


@dataclass(frozen=True)
class ProcessOptions:
    remove_background: bool = False
    rembg_binary: Path | None = None
    rembg_model: str = "isnet-general-use"
    upscale: bool = False
    esrgan_binary: Path | None = None
    esrgan_model: str = "realesrgan-x4plus-anime"
    target_size: tuple[int, int] = (5000, 5500)
    margin: float = .07
    feather: float = 0.0


def _executable(path: Path | None, name: str) -> Path:
    if path is None or not path.is_file():
        raise RuntimeError(f"{name} tool must be installed and selected explicitly.")
    return path.resolve()


def _run(command: list[str], folder: Path, timeout: int) -> None:
    try:
        result = subprocess.run(command, cwd=folder, capture_output=True, text=True,
                                timeout=timeout, check=False, shell=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Local image tool did not run or timed out.") from exc
    if result.returncode != 0:
        raise RuntimeError("Local image tool failed. Check its models and GPU setup.")


def _remove_background(image: Image.Image, tool: Path, model: str) -> Image.Image:
    if model not in {"isnet-general-use", "birefnet-general", "isnet-anime"}:
        raise ValueError("Unrecognized rembg model.")
    with tempfile.TemporaryDirectory(prefix="podbot-bg-") as tmp:
        folder = Path(tmp)
        src, dst = folder / "src.png", folder / "cutout.png"
        image.convert("RGB").save(src)
        # -dc is rembg's documented edge color decontamination. Alpha matting
        # is often unnecessary for current isnet/birefnet weights.
        _run([str(tool), "i", "-m", model, "-dc", str(src), str(dst)],
             tool.parent, 600)
        if not dst.is_file():
            raise RuntimeError("Background removal produced no PNG.")
        with Image.open(dst) as processed:
            processed.load()
            return processed.convert("RGBA")


def _upscale(image: Image.Image, tool: Path, model: str) -> Image.Image:
    if model not in {"realesrgan-x4plus", "realesrgan-x4plus-anime"}:
        raise ValueError("Unsupported Real-ESRGAN model.")
    with tempfile.TemporaryDirectory(prefix="podbot-sr-") as tmp:
        folder = Path(tmp)
        src, dst = folder / "rgb.png", folder / "upscaled.png"
        rgba = image.convert("RGBA")
        rgba.convert("RGB").save(src)
        _run([str(tool), "-i", str(src), "-o", str(dst),
              "-n", model, "-s", "4"], tool.parent, 600)
        if not dst.is_file():
            raise RuntimeError("Upscaler produced no output PNG.")
        with Image.open(dst) as final:
            final.load()
            result = final.convert("RGBA")
        alpha = rgba.getchannel("A").resize(result.size, Image.Resampling.LANCZOS)
        result.putalpha(alpha)
        return result


def compose_print(image: Image.Image, target: Path, *,
                  size: tuple[int, int] = (5000, 5500),
                  margin: float = .07, feather: float = 0.0) -> dict:
    """Crop visible bounds, fit inside safe printable margins, save 300-DPI metadata."""
    if not 0 <= margin <= .20:
        raise ValueError("Safety margin must be between 0% and 20%.")
    if not 0 <= feather <= 2.0:
        raise ValueError("Feathering must be 0 to 2 pixels.")
    if min(size) < 64 or max(size) > 14000:
        raise ValueError("Unsupported output size.")
    rgba = ImageOps.exif_transpose(image).convert("RGBA")
    source_size = list(rgba.size)
    if rgba.width > 20000 or rgba.height > 20000:
        raise ValueError("Image too large to process safely.")
    box = rgba.getchannel("A").getbbox()
    if not box:
        raise ValueError("Artwork is fully transparent.")
    art = rgba.crop(box)
    if feather:
        art.putalpha(art.getchannel("A").filter(ImageFilter.GaussianBlur(feather)))
    inner = (
        int(size[0] * (1 - 2 * margin)),
        int(size[1] * (1 - 2 * margin)),
    )
    scaled = ImageOps.contain(art, inner, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(scaled, ((size[0] - scaled.width) // 2,
                                    (size[1] - scaled.height) // 2))
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target, "PNG", dpi=(300, 300), optimize=True)
    return {"source_size": source_size, "cropped_size": list(art.size),
            "print_size": list(size), "margin": margin,
            "processing": "lanczos resampling; no restoration claimed"}


def process_image(image: Image.Image, target: Path, options: ProcessOptions) -> dict:
    """No hidden downloads, fallbacks or destruction of the original source."""
    if options.remove_background and options.rembg_binary is None:
        raise RuntimeError("rembg tool is not configured; install it first.")
    if options.upscale and options.esrgan_binary is None:
        raise RuntimeError("Real-ESRGAN tool is not configured; select its EXE first.")
    rgba = image.copy()
    steps = []
    if options.remove_background:
        tool = _executable(options.rembg_binary, "rembg")
        rgba = _remove_background(rgba, tool, options.rembg_model)
        steps.append(f"rembg:{options.rembg_model}")
    if options.upscale:
        tool = _executable(options.esrgan_binary, "Real-ESRGAN")
        rgba = _upscale(rgba, tool, options.esrgan_model)
        steps.append(f"Real-ESRGAN:{options.esrgan_model}")
    details = compose_print(rgba, target, size=options.target_size,
                            margin=options.margin, feather=options.feather)
    details["steps"] = steps or ["crop", "lanczos"]
    return details



def process_stored_design(design_id: str, options: ProcessOptions,
                          root: Path | None = None) -> dict:
    """Rebuild from immutable source, never silently overwrite prior print assets."""
    import json
    import re
    import uuid

    from podbot.audit import audit_image, fingerprint
    from podbot.settings import designs_directory
    from podbot.storage import save_manifest

    if not re.fullmatch(r"[0-9a-f]{32}", design_id):
        raise ValueError("Invalid design ID.")
    folder = (root or designs_directory()) / design_id
    manifest = folder / "manifest.json"
    record = json.loads(manifest.read_text(encoding="utf-8"))
    if record.get("id") != design_id:
        raise ValueError("Manifest ID mismatch.")
    source = Path(record["source_file"])
    if not source.is_file():
        raise ValueError("Original source PNG is missing.")
    target = folder / f"processed_{uuid.uuid4().hex[:12]}.png"
    try:
        with Image.open(source) as image:
            original = image.convert("RGBA")
            details = process_image(original, target, options)
        with Image.open(target) as processed:
            fingerprint_value = fingerprint(processed)
            audits = {
                platform: [c.to_dict() for c in audit_image(processed, platform)]
                for platform in ("redbubble", "teepublic")
            }
        record["print_file"] = str(target.resolve())
        record["output_size"] = list(options.target_size)
        record["processing"] = details
        record["fingerprint"] = fingerprint_value
        record["quality_checks"] = audits
        record["platform_status"] = {"redbubble": "draft", "teepublic": "draft"}
        record["approval_evidence"] = {}
        record["quality_warning"] = (
            "Reprocessing invalidated approvals. Inspect alpha, actual source resolution "
            "and both platform quality reports before approving."
        )
        save_manifest(folder, record)
        return record
    except Exception:
        target.unlink(missing_ok=True)
        raise
