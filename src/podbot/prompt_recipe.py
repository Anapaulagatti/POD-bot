"""CPU-only, deterministic POD prompt recipes (no LLM, model weights or network)."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass

RECIPE_VERSION = 1
STYLES = {
    "minimal-vector": "minimal flat vector illustration with crisp closed shapes",
    "line-art": "clean high-contrast hand-drawn line art",
    "vintage-screenprint": "vintage screen-print artwork with distressed details kept inside shapes",
    "paper-cut": "layered paper-cut illustration with clean boundaries",
}
LAYOUTS = {
    "centered": "single centered subject with generous negative space",
    "badge": "compact emblem or badge composition with balanced margins",
    "stacked": "vertically stacked composition for a portrait T-shirt print",
}
BACKGROUNDS = {
    "transparent": "isolated artwork on a genuinely transparent alpha background",
    "flat-white": "isolated artwork on a uniformly flat pure white background, easy to remove",
}
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}\Z")


def _single_line(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Prompt field must be text.")
    return " ".join(value.split())


@dataclass(frozen=True)
class PromptRecipe:
    subject: str
    style: str = "minimal-vector"
    layout: str = "centered"
    colors: tuple[str, ...] = ("#123047", "#F4AC45", "#F5F0DE")
    background: str = "transparent"
    text_rule: str = "none"
    original_text: str = ""
    version: int = RECIPE_VERSION

    @classmethod
    def from_dict(cls, payload: dict) -> PromptRecipe:
        if not isinstance(payload, dict):
            raise ValueError("Prompt recipe must be an object.")
        allowed = set(cls.__dataclass_fields__)
        if set(payload) - allowed:
            raise ValueError("Unknown prompt recipe fields.")
        colors = payload.get("colors", cls.__dataclass_fields__["colors"].default)
        if not isinstance(colors, (list, tuple)):
            raise ValueError("Palette must be a list of HEX colors.")
        try:
            return cls(**{**payload, "colors": tuple(colors)})
        except TypeError as exc:
            raise ValueError("Prompt recipe has missing or invalid fields.") from exc

    def validated(self) -> PromptRecipe:
        subject = _single_line(self.subject)
        original_text = _single_line(self.original_text)
        if self.version != RECIPE_VERSION or type(self.version) is not int:
            raise ValueError("Unsupported prompt recipe version.")
        if not 5 <= len(subject) <= 180:
            raise ValueError("Subject must be 5-180 characters.")
        if self.style not in STYLES or self.layout not in LAYOUTS:
            raise ValueError("Unsupported prompt style or layout.")
        if self.background not in BACKGROUNDS:
            raise ValueError("Unsupported background selection.")
        if self.text_rule not in {"none", "original"}:
            raise ValueError("Unknown lettering policy.")
        if self.text_rule == "original" and not 1 <= len(original_text) <= 80:
            raise ValueError("Original lettering must be 1-80 characters.")
        if self.text_rule == "none" and original_text:
            raise ValueError("Text must be empty when lettering is disabled.")
        if not 1 <= len(self.colors) <= 6:
            raise ValueError("Palette must contain 1-6 HEX colors.")
        colors = tuple(str(c).upper() for c in self.colors)
        if not all(HEX_COLOR.fullmatch(c) for c in colors):
            raise ValueError("Palette accepts only #RRGGBB colors.")
        if len(set(colors)) != len(colors):
            raise ValueError("Duplicate HEX colors in palette.")
        if any(ord(char) < 32 for char in subject + original_text):
            raise ValueError("Prompt contains control characters.")
        return PromptRecipe(
            subject=subject, style=self.style, layout=self.layout,
            colors=colors, background=self.background,
            text_rule=self.text_rule, original_text=original_text,
            version=self.version,
        )

    def to_manifest(self) -> dict:
        value = self.validated()
        payload = asdict(value)
        payload["colors"] = list(value.colors)
        return payload


def build_prompt(recipe: PromptRecipe) -> str:
    item = recipe.validated()
    palette = ", ".join(item.colors)
    lettering = (
        "No letters, words, typography, watermarks, brand marks or logos."
        if item.text_rule == "none"
        else f"Render ONLY the user-original lettering {json.dumps(item.original_text, ensure_ascii=False)} "
             "accurately and legibly; no additional text, brand logos or watermarks."
    )
    result = (
        f"Original artwork for print-on-demand apparel. Subject: {item.subject}. "
        f"Visual style: {STYLES[item.style]}. Composition: {LAYOUTS[item.layout]}. "
        f"Use a restrained palette of at most {len(item.colors)} colors: {palette}. "
        f"Background: {BACKGROUNDS[item.background]}; no cast shadows, gradients, "
        f"vignette or photographic scenery. {lettering} "
        "Strong silhouette, clean edges, ample print-safe margins. "
        "Do not include recognizable copyrighted characters or trademarks."
    )
    if len(result) > 2048:
        raise ValueError("Structured prompt exceeded 2048 characters.")
    return result


def recipe_sha256(recipe: PromptRecipe) -> str:
    canonical = json.dumps(
        recipe.to_manifest(), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
