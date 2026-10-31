"""POD creation pipeline. Generated image is NOT automatically print-ready."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps

from podbot.providers import ImageProvider
from podbot.seo import SEOMetadata, gemini_seo, local_seo
from podbot.settings import designs_directory
from podbot.storage import save_manifest


PRINT_SIZE = (4500, 5400)


def prepare_print_image(image: Image.Image, target: Path, size: tuple[int, int] = PRINT_SIZE) -> bool:
    """Upscale/fit to transparent canvas; keep alpha if present, never fake cutout quality.

    Note: Resizing does not add detail, and an opaque AI image remains opaque.
    """
    if image.width < 1 or image.height < 1:
        raise ValueError("Invalid image dimensions.")
    has_alpha = image.mode in {"RGBA", "LA"} or "transparency" in image.info
    rgba = image.convert("RGBA")
    fitted = ImageOps.contain(rgba, (int(size[0] * .9), int(size[1] * .9)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(fitted, ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2))
    canvas.save(target, format="PNG", optimize=True, dpi=(300, 300))
    return has_alpha


def create_draft(
    prompt: str,
    niche: str,
    keywords: str,
    provider: ImageProvider,
    seo_mode: str = "local",
    gemini_key: str = "",
    root: Path | None = None,
) -> dict:
    prompt = prompt.strip()
    if len(prompt) < 5:
        raise ValueError("Please enter a descriptive prompt (minimum 5 characters).")
    if seo_mode not in {"local", "gemini"}:
        raise ValueError("Unknown SEO mode.")
    # Validate metadata and tokens before any costly image request.
    if seo_mode == "gemini":
        metadata = gemini_seo(niche, keywords, prompt, gemini_key)
    else:
        metadata = local_seo(niche, keywords, prompt)
    image = provider.generate(prompt)
    if image.width > 20000 or image.height > 20000:
        raise ValueError("Input image dimensions exceed the safe processing limit.")
    design_id = uuid.uuid4().hex
    folder = (root or designs_directory()) / design_id
    folder.mkdir(parents=True, exist_ok=False)
    source_path = folder / "source.png"
    print_path = folder / "print_4500x5400.png"
    try:
        image.save(source_path, format="PNG")
        has_alpha = prepare_print_image(image, print_path)
        original_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        record = {
            "id": design_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "prompt": prompt,
            "niche": niche.strip(),
            "keywords": keywords.strip(),
            "provider": provider.name,
            "seo_mode": seo_mode,
            "seo": metadata.to_dict() if isinstance(metadata, SEOMetadata) else metadata,
            "source_file": str(source_path.resolve()),
            "print_file": str(print_path.resolve()),
            "source_sha256": original_hash,
            "original_size": list(image.size),
            "output_size": list(PRINT_SIZE),
            "source_has_alpha": has_alpha,
            "quality_warning": (
                "Opaque background detected: manual background removal/inspection required. "
                "Upscaling does not increase image detail."
                if not has_alpha else "Inspect edges and resolution before listing."
            ),
            "platform_status": {"redbubble": "draft", "teepublic": "draft"},
        }
        save_manifest(folder, record)
        return record
    except Exception:
        # A failed draft must not appear in the queue.
        import shutil
        shutil.rmtree(folder, ignore_errors=True)
        raise
