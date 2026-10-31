"""Import own designs into POD review queue without an image API request."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from podbot.pipeline import create_draft
from podbot.settings import designs_directory
from podbot.storage import save_manifest


@dataclass
class LocalImageProvider:
    path: Path
    name: str = "local-file-import"

    def generate(self, prompt: str) -> Image.Image:
        source = self.path.expanduser().resolve()
        if source.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise ValueError("Only PNG, JPEG and WebP image imports are supported.")
        if not source.is_file() or source.stat().st_size > 30 * 1024 * 1024:
            raise ValueError("Import image is missing or larger than 30 MB.")
        try:
            with Image.open(source) as img:
                if img.width * img.height > 50_000_000:
                    raise ValueError("Import exceeds 50 megapixels.")
                img.load()
                return img.copy()
        except (UnidentifiedImageError, OSError) as exc:
            raise ValueError("Cannot read the chosen image.") from exc


def import_design(
    path: Path, niche: str, keywords: str = "", description: str = "",
    *, root: Path | None = None,
) -> dict:
    source = path.expanduser().resolve()
    prompt = description.strip() or f"Original artwork imported from local file for {niche.strip()}"
    provider = LocalImageProvider(source)
    # Validate file before creating SEO or output directory.
    preview = provider.generate(prompt)
    preview.close()
    record = create_draft(
        prompt, niche, keywords, provider, seo_mode="local",
        root=root or designs_directory(),
    )
    file = Path(record["print_file"]).parent / "manifest.json"
    record["ai_generated"] = False
    record["imported_from_local_file"] = source.name
    record["model_id"] = "local-import"
    save_manifest(file.parent, record)
    return record
