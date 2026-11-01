"""No-GPU POD prompt recipe regression tests and durable provenance."""

import hashlib
import json

import pytest
from PIL import Image, ImageDraw

from podbot.pipeline import create_draft
from podbot.prompt_recipe import PromptRecipe, build_prompt, recipe_sha256
from podbot.storage import list_designs


class FakeProvider:
    name = "offline-fixture"

    def __init__(self):
        self.calls = []

    def generate(self, prompt):
        self.calls.append(prompt)
        canvas = Image.new("RGBA", (120, 130), (0, 0, 0, 0))
        ImageDraw.Draw(canvas).rectangle((35, 30, 95, 96), fill=(40, 80, 120, 255))
        return canvas


def sample_recipe(**updates):
    data = {
        "subject": "Original mountain sunrise with pine tree",
        "style": "minimal-vector",
        "layout": "centered",
        "colors": ["#112233", "#AABBCC", "#FFCC00"],
        "background": "transparent",
        "text_rule": "none",
        "original_text": "",
        "version": 1,
    }
    data.update(updates)
    return PromptRecipe.from_dict(data)


def test_build_structured_prompt_is_deterministic_and_cpu_only():
    recipe = sample_recipe()
    result = build_prompt(recipe)
    assert result == build_prompt(sample_recipe(colors=tuple(recipe.colors)))
    assert "genuinely transparent alpha" in result
    assert "#112233, #AABBCC, #FFCC00" in result
    assert "No letters, words" in result
    assert "no cast shadows" in result
    assert recipe_sha256(recipe) == recipe_sha256(PromptRecipe.from_dict(recipe.to_manifest()))
    assert len(result) < 2048


@pytest.mark.parametrize("invalid", [
    {"subject": "a"},
    {"style": "photoreal"},
    {"layout": "billboard"},
    {"background": "unknown"},
    {"colors": []},
    {"colors": ["#123456"] * 7},
    {"colors": ["#123456", "#123456"]},
    {"colors": ["javascript:alert(1)"]},
    {"text_rule": "wrong"},
    {"text_rule": "original", "original_text": ""},
    {"text_rule": "none", "original_text": "hello"},
    {"version": 99},
])
def test_invalid_recipes_rejected_before_generation(invalid):
    with pytest.raises(ValueError):
        build_prompt(sample_recipe(**invalid))


def test_original_lettering_is_explicit_and_json_escaped():
    prompt = build_prompt(sample_recipe(text_rule="original", original_text='Go "Hiking"!'))
    assert 'Go \\"Hiking\\"!' in prompt
    assert "No letters, words" not in prompt


def test_recipe_manifest_round_trip_and_hash(tmp_path):
    recipe = sample_recipe(background="flat-white")
    prompt = build_prompt(recipe)
    provider = FakeProvider()
    saved = create_draft(prompt, "nature", "mountain", provider, root=tmp_path,
                         prompt_recipe=recipe.to_manifest())
    assert provider.calls == [prompt]
    assert saved["prompt_recipe"]["background"] == "flat-white"
    assert saved["prompt_recipe_sha256"] == recipe_sha256(recipe)
    assert saved["prompt_sent_sha256"] == hashlib.sha256(prompt.encode()).hexdigest()
    persisted = list_designs(tmp_path)[0]
    assert persisted["prompt_recipe"] == saved["prompt_recipe"]
    assert persisted["prompt"] == prompt
    assert json.loads((tmp_path / saved["id"] / "manifest.json").read_text())["prompt_recipe"]


def test_inconsistent_recipe_or_background_never_calls_paid_provider(tmp_path):
    provider = FakeProvider()
    recipe = sample_recipe()
    with pytest.raises(ValueError, match="differs"):
        create_draft("arbitrary long artistic prompt", "nature", "mountain", provider,
                     root=tmp_path, prompt_recipe=recipe.to_manifest())
    with pytest.raises(ValueError, match="conflicts"):
        create_draft(build_prompt(recipe), "nature", "mountain", provider,
                     root=tmp_path, flat_background_prompt=True,
                     prompt_recipe=recipe.to_manifest())
    assert not provider.calls
    assert list(tmp_path.iterdir()) == []


def test_unstructured_prompts_still_supported_and_flat_suffix(tmp_path):
    provider = FakeProvider()
    saved = create_draft(
        "my original alpine flower", "nature", "flowers", provider, root=tmp_path,
        flat_background_prompt=True,
    )
    assert saved["prompt_recipe"] is None
    assert saved["prompt_recipe_sha256"] is None
    assert provider.calls[0] != saved["prompt"]
    assert saved["flat_background_prompt"] is True
    assert saved["prompt_sent_sha256"] == hashlib.sha256(
        provider.calls[0].encode("utf-8")
    ).hexdigest()


def test_extra_recipe_keys_rejected():
    with pytest.raises(ValueError, match="Unknown"):
        PromptRecipe.from_dict({"subject": "Original mountain", "api_key": "SECRET"})
