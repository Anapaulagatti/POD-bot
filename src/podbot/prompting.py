"""Opt-in prompt shaping; only modifies the sent prompt, not source SEO text."""

FLAT_BACKGROUND_SUFFIX = (
    "Isolated central subject on a flat solid white background; "
    "clear crisp silhouette; no gradients, textures, vignette, scenery, or cast shadows. "
    "Keep all lettering legible and avoid brands, logos, or copyrighted characters."
)


def prepare_image_prompt(prompt: str, *, flat_background: bool = False) -> str:
    prompt = prompt.strip()
    if not flat_background:
        return prompt
    if len(prompt) + len(FLAT_BACKGROUND_SUFFIX) + 2 > 2048:
        raise ValueError("Prompt is too long to append the flat background instructions.")
    return prompt + "\n\n" + FLAT_BACKGROUND_SUFFIX
