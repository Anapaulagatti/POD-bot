"""POD creation pipeline. Generated image is NOT automatically print-ready."""

from __future__ import annotations

import hashlib
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image

from podbot.audit import audit_image, find_blocked_terms, fingerprint, get_blocklist
from podbot.processing import compose_print
from podbot.providers import ImageProvider
from podbot.seo import SEOMetadata, gemini_seo, local_seo
from podbot.settings import designs_directory
from podbot.storage import save_manifest

PRINT_SIZE = (5000, 5500)


def prepare_print_image(
    image: Image.Image, target: Path, size: tuple[int, int] = PRINT_SIZE
) -> bool:
    """Compatibility helper: shared alpha-cropped, 7% margin print engine."""
    has_alpha = image.convert("RGBA").getchannel("A").getextrema()[0] < 255
    compose_print(image, target, size=size)
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
    blocked = find_blocked_terms(f"{prompt} {niche} {keywords}", get_blocklist())
    if blocked:
        raise ValueError("blocklist requires review: " + ", ".join(blocked[:5]))
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
    print_path = folder / "print_5000x5500.png"
    try:
        image.save(source_path, format="PNG")
        has_alpha = image.convert("RGBA").getchannel("A").getextrema()[0] < 255
        print_details = compose_print(image, print_path, size=PRINT_SIZE)
        original_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        record = {
            "id": design_id,
            "created_at": datetime.now(UTC).isoformat(),
            "prompt": prompt,
            "niche": niche.strip(),
            "keywords": keywords.strip(),
            "provider": provider.name,
            "seo_mode": seo_mode,
            "seo": metadata.to_dict() if isinstance(metadata, SEOMetadata) else metadata,
            "source_file": str(source_path.resolve()),
            "print_file": str(print_path.resolve()),
            "source_sha256": original_hash,
            "fingerprint": fingerprint(image),
            "fingerprint_algorithm": "v2:luminance-gray+alpha",
            "original_size": list(image.size),
            "output_size": list(PRINT_SIZE),
            "source_has_alpha": has_alpha,
            "quality_warning": (
                "Opaque background detected: manual background removal/inspection required. "
                "Upscaling does not increase image detail."
                if not has_alpha else "Inspect edges and resolution before listing."
            ),
            "platform_status": {"redbubble": "draft", "teepublic": "draft"},
            "rights_confirmed_at": None,
            "ai_generated": True,
            "processing": {**print_details, "steps": ["alpha-crop", "safe-margin", "lanczos"]},
        }
        with Image.open(print_path) as printed:
            record["quality_checks"] = {
                platform: [check.to_dict() for check in audit_image(
                    printed, platform, source_size=image.size, opaque_source=not has_alpha
                )] for platform in ("redbubble", "teepublic")
            }
        save_manifest(folder, record)
        return record
    except Exception:
        # A failed draft must not appear in the queue.
        shutil.rmtree(folder, ignore_errors=True)
        raise
