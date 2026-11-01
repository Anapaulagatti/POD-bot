"""Optional CPU-only VTracer SVG export. No ML, downloads or new dependencies."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageOps

from podbot.settings import designs_directory

SVG_NAMESPACE = "http://www.w3.org/2000/svg"
MAX_VECTOR_BYTES = 8 * 1024 * 1024
ALLOWED_SVG_TAGS = {
    "svg", "g", "path", "rect", "circle", "ellipse", "polygon", "polyline",
    "line", "defs", "clipPath", "title", "desc",
}


def _verify_svg(path: Path) -> None:
    if not path.is_file() or not 30 <= path.stat().st_size <= MAX_VECTOR_BYTES:
        raise RuntimeError("VTracer SVG is empty, missing or exceeds the 8 MB safety limit.")
    raw = path.read_bytes()
    lower = raw.lower()
    if b"<!doctype" in lower or b"<!entity" in lower:
        raise RuntimeError("SVG contains disallowed DTD or ENTITY declarations.")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        raise RuntimeError("VTracer produced invalid SVG.") from None
    if root.tag != f"{{{SVG_NAMESPACE}}}svg":
        raise RuntimeError("VTracer output is not a standalone SVG.")
    for element in root.iter():
        if element.tag.split("}")[-1] not in ALLOWED_SVG_TAGS:
            raise RuntimeError("SVG contains unexpected elements.")
        for name, value in element.attrib.items():
            local = name.split("}")[-1].casefold()
            if (local.startswith("on") or local in {"href", "base", "src"}
                    or "url(" in value.casefold() or "@import" in value.casefold()):
                raise RuntimeError("SVG references external or active content.")


def export_vector(
    design_id: str, tool: Path, *,
    max_colors: int = 6, root: Path | None = None,
) -> Path:
    """Trace the approved print cutout, keeping print assets and approval untouched.

    VTracer CLI is installed/selected separately by the operator; it is not bundled.
    Tracing is intended for flat graphics and does not establish commercial rights.
    """
    if not re.fullmatch(r"[0-9a-f]{32}", design_id):
        raise ValueError("Invalid design ID.")
    if type(max_colors) is not int or not 2 <= max_colors <= 6:
        raise ValueError("Vector palette size must be between 2 and 6.")
    if not isinstance(tool, Path) or not tool.is_file():
        raise ValueError("Select a locally installed VTracer executable.")
    folder = (root or designs_directory()) / design_id
    manifest = folder / "manifest.json"
    record = json.loads(manifest.read_text(encoding="utf-8"))
    if record.get("id") != design_id:
        raise ValueError("Manifest ID mismatch.")
    source = Path(record.get("print_file", ""))
    # Never follow a tampered manifest path outside this design's own folder.
    if source.suffix.lower() != ".png" or source.resolve().parent != folder.resolve():
        raise ValueError("Print image must be a PNG inside the selected design folder.")
    if not source.is_file():
        raise FileNotFoundError("Processed print PNG is missing; export requires a cutout.")
    with tempfile.TemporaryDirectory(prefix="podbot-vector-") as work:
        directory = Path(work)
        input_path = directory / "source.png"
        output_path = directory / "converted.svg"
        with Image.open(source) as image:
            if image.width > 20000 or image.height > 20000:
                raise ValueError("Print image dimensions are unsafe.")
            # Scale the original PNG before allocating a full-size RGBA buffer.
            small = ImageOps.contain(image, (1600, 1600), Image.Resampling.LANCZOS)
            original = small.convert("RGBA")
            if original.getchannel("A").getextrema()[0] == 255:
                raise ValueError(
                    "Print artwork has no transparent cutout. Remove the background "
                    "and review the PNG before vectorizing."
                )
            original.save(input_path, "PNG")
        try:
            finished = subprocess.run(
                [
                    str(tool.resolve()), str(input_path), str(output_path),
                    "--preset", "poster", "--max-colors", str(max_colors),
                    "--filter-speckle", "4",
                ],
                check=False, shell=False, capture_output=True, timeout=180,
                cwd=directory,
            )
        except (OSError, subprocess.TimeoutExpired):
            raise RuntimeError("VTracer failed or exceeded the 180-second CPU limit.") from None
        if finished.returncode != 0:
            raise RuntimeError(
                "VTracer CLI rejected the request. Verify its version supports "
                "--max-colors (v1 alpha) and that the executable is trusted."
            )
        _verify_svg(output_path)
        target = folder / f"vector_preview_{uuid.uuid4().hex[:10]}.svg"
        # Do not edit the manifest or overwrite marketplace-approved artwork.
        target.write_bytes(output_path.read_bytes())
        return target
