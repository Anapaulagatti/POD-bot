"""Fast local heuristics for POD assets; NOT legal clearance or a print proof."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps, ImageStat

from podbot.settings import data_directory

# Platform guides checked 2026-10-31. Details at docs/PUBLISHING_POLICY.md.
MIN_CANVAS = {"redbubble": (2400, 3200), "teepublic": (5000, 5500)}
SHIRTS = ((255, 255, 255), (29, 29, 30), (24, 39, 69), (135, 139, 142))


@dataclass(frozen=True)
class Check:
    name: str
    level: str
    value: str
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


def _normalized(value: str) -> str:
    decomp = unicodedata.normalize("NFKD", value.casefold())
    plain = "".join(x for x in decomp if not unicodedata.combining(x))
    return " ".join(re.findall(r"[\w]+", plain, flags=re.UNICODE))


def find_blocked_terms(text: str, terms: list[str]) -> list[str]:
    """Exact normalized PHRASE match with word boundaries, not substring match."""
    normalized = " " + _normalized(text) + " "
    return [
        term for term in terms
        if _normalized(term) and f" {_normalized(term)} " in normalized
    ]


def get_blocklist(path: Path | None = None) -> list[str]:
    file = path or (data_directory() / "blocklist.txt")
    if not file.exists():
        return []
    return [
        line.strip() for line in file.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ][:3000]


def _dhash(image: Image.Image) -> str:
    pixels = list(image.convert("L").resize((9, 8), Image.Resampling.LANCZOS).tobytes())
    result = 0
    for y in range(8):
        for x in range(8):
            result = (result << 1) | int(pixels[y * 9 + x] > pixels[y * 9 + x + 1])
    return f"{result:016x}"


def fingerprint(image: Image.Image) -> str:
    """Versioned dHash: gray-composited luminance PLUS the original alpha mask.

    White motifs cannot disappear into a white-only background. The alpha signature
    is also effective for transparent lettering and different outline shapes.
    """
    # Resize in the source mode before allocating RGBA buffers. Fingerprints
    # compare silhouettes, not native-resolution print pixels.
    sample = ImageOps.contain(image, (128, 128), Image.Resampling.LANCZOS)
    rgba = sample.convert("RGBA")
    preview = Image.new("RGBA", rgba.size, (127, 127, 127, 255))
    preview.alpha_composite(rgba)
    return "v2:" + _dhash(preview.convert("RGB")) + _dhash(rgba.getchannel("A"))


def hash_distance(a: str, b: str) -> int:
    if not (a.startswith("v2:") and b.startswith("v2:") and
            re.fullmatch(r"v2:[0-9a-f]{32}", a) and
            re.fullmatch(r"v2:[0-9a-f]{32}", b)):
        raise ValueError("Only version 2 fingerprints can be compared.")
    return (int(a[3:19], 16) ^ int(b[3:19], 16)).bit_count() + (
        int(a[19:], 16) ^ int(b[19:], 16)
    ).bit_count()



def audit_image(image: Image.Image, platform: str, *,
                source_size: tuple[int, int] | None = None,
                opaque_source: bool = False) -> list[Check]:
    if platform not in MIN_CANVAS:
        raise ValueError("Unsupported marketplace.")
    if image.width <= 0 or image.height <= 0:
        raise ValueError("Empty image.")
    # Downsample for statistical scans; check real full-size dimensions separately.
    small = ImageOps.contain(image, (512, 512), Image.Resampling.LANCZOS).convert("RGBA")
    alpha = small.getchannel("A")
    box = alpha.getbbox()
    output: list[Check] = []
    required = MIN_CANVAS[platform]
    size_ok = image.width >= required[0] and image.height >= required[1]
    output.append(Check("canvas", "pass" if size_ok else "fail",
                        f"{image.width}x{image.height}",
                        f"Target preset {required[0]}x{required[1]} px."))
    if not box:
        return output + [Check("background", "fail", "empty", "No artwork visible.")]
    hist = alpha.histogram()
    nonopaque = sum(hist[:255]) / max(1, small.width * small.height)
    # Measure transparency WITHIN actual visible bounds to detect an opaque rectangle
    # pasted into an otherwise transparent outer margin.
    cropped = alpha.crop(box)
    c_hist = cropped.histogram()
    clear_inside = sum(c_hist[:8]) / max(1, cropped.width * cropped.height)
    is_cutout = clear_inside >= 0.05
    output.append(Check("background", "pass" if is_cutout else "fail",
                        f"clear_inside={clear_inside:.3f}, alpha_fraction={nonopaque:.3f}",
                        "Detects rectangular opaque artwork/background. "
                        "Rectangular designs may need a manual cutout/rework."))
    touches = any(alpha.crop(b).getbbox() for b in (
        (0, 0, 1, small.height), (small.width - 1, 0, small.width, small.height),
        (0, 0, small.width, 1), (0, small.height - 1, small.width, small.height),
    ))
    output.append(Check("edge_touch", "fail" if touches else "pass", str(bool(touches)),
                        "Printed design should not touch any edge of the canvas."))
    coverage = (box[2] - box[0]) * (box[3] - box[1]) / (small.width * small.height)
    output.append(Check("occupancy", "warn" if coverage < .30 or coverage > .95 else "pass",
                        f"{coverage:.1%}", "Artwork bounding box relative to full canvas."))
    if platform == "teepublic":
        aw = round((box[2] - box[0]) * image.width / small.width)
        ah = round((box[3] - box[1]) * image.height / small.height)
        ok = aw >= 1500 and ah >= 1995
        output.append(Check("visible_area", "pass" if ok else "fail", f"{aw}x{ah}",
                            "TeePublic requests >=1500x1995 visible artwork pixels."))
    if source_size and min(source_size) > 0:
        scale = max(image.width / source_size[0], image.height / source_size[1])
        output.append(Check(
            "native_resolution", "warn" if scale > 1.5 else "pass",
            f"{source_size[0]}x{source_size[1]} native, {scale:.1f}x",
            "Artwork upscaled from native source; interpolation cannot restore original detail.",
        ))
    if opaque_source:
        output.append(Check(
            "source_background", "warn", "original image was opaque",
            "Check the original source and background removal quality.",
        ))
    # Counts and contrast are advisory only; thresholds are user-calibratable later.
    core = small.convert("RGB").quantize(colors=16)
    colors = sum(1 for count in core.histogram() if count)
    output.append(Check("palette", "pass" if colors <= 12 else "warn",
                        str(colors), "Advisory palette complexity estimate, not legal safety."))
    core_luma = ImageStat.Stat(small.convert("L")).mean[0]
    output.append(Check("contrast", "warn" if 100 < core_luma < 150 else "pass",
                        f"gray={core_luma:.1f}", "Always preview on light and dark fabric."))
    return output


def make_color_preview(artwork: Image.Image, target: Path,
                       tile: tuple[int, int] = (360, 440)) -> Path:
    if tile[0] < 100 or tile[1] < 100:
        raise ValueError("Preview tile too small.")
    width, height = tile
    preview = Image.new("RGB", (width * 2, height * 2), "white")
    design = ImageOps.contain(artwork.convert("RGBA"),
                              (int(width * .72), int(height * .62)),
                              Image.Resampling.LANCZOS)
    for index, shade in enumerate(SHIRTS):
        x, y = (index % 2) * width, (index // 2) * height
        ImageDraw.Draw(preview).rectangle((x, y, x + width - 1, y + height - 1),
                                          fill=shade)
        preview.paste(design,
                      (x + (width - design.width) // 2,
                       y + (height - design.height) // 2),
                      mask=design.getchannel("A"))
    target.parent.mkdir(parents=True, exist_ok=True)
    preview.save(target, "PNG")
    return target



def near_duplicates(
    entry: dict, other_entries: list[dict], max_distance: int = 8
) -> list[str]:
    """Advisory local dHash overlap; no external similarity server."""
    current = entry.get("fingerprint")
    if not isinstance(current, str) or not re.fullmatch(r"v2:[0-9a-f]{32}", current):
        return []
    matches = []
    for other in other_entries:
        candidate = other.get("fingerprint")
        if (other.get("id") != entry.get("id") and isinstance(candidate, str)
                and re.fullmatch(r"v2:[0-9a-f]{32}", candidate)):
            try:
                if hash_distance(current, candidate) < max_distance:
                    matches.append(str(other.get("id")))
            except ValueError:
                continue
    return matches
