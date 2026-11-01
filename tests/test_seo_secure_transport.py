"""Prevent authenticated HTTP redirect regressions, including Gemini SEO."""

from __future__ import annotations

import ast
import json
import urllib.request
from pathlib import Path

import pytest

from podbot import seo
from podbot.auth_transport import NoCredentialRedirect


class FakeResponse:
    def __init__(self, data: bytes):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, limit: int | None = None):
        return self.data if limit is None else self.data[:limit]


def test_gemini_seo_never_uses_redirect_following_urlopen(monkeypatch):
    sent = []
    reserved = []
    body = json.dumps({
        "candidates": [{
            "content": {
                "parts": [{"text": json.dumps({
                    "title": "Original Floral Design",
                    "description": "An original floral composition suitable for a print.",
                    "tags": ["flowers", "art", "garden"],
                })}]
            }
        }]
    }).encode()

    def fake_open(request, *, timeout):
        sent.append((request, timeout))
        return FakeResponse(body)

    monkeypatch.setattr(seo, "open_authenticated", fake_open)
    monkeypatch.setattr(seo, "reserve_paid_request", lambda name: reserved.append(name))
    monkeypatch.setattr(
        urllib.request, "urlopen",
        lambda *_args, **_kwargs: pytest.fail("Gemini SEO used unsafe urlopen"),
    )
    result = seo.gemini_seo("flower", "garden,original", "blue floral pattern", api_key="secret")
    assert result.title == "Original Floral Design"
    assert reserved == ["gemini"]
    assert len(sent) == 1
    request, timeout = sent[0]
    assert request.get_method() == "POST"
    assert request.get_header("X-goog-api-key") == "secret"
    assert request.full_url.startswith("https://generativelanguage.googleapis.com/")
    assert "secret" not in request.full_url
    assert timeout == 90


def test_gemini_seo_uses_no_redirect_transport_when_real_call_is_wired(monkeypatch):
    captured = []

    class FakeOpener:
        def open(self, request, timeout):
            captured.append((request, timeout))
            return FakeResponse(json.dumps({
                "candidates": [{"content": {"parts": [{"text": json.dumps({
                    "title": "Original Landscape",
                    "description": "An original landscape work.",
                    "tags": ["landscape", "illustration"],
                })}]}}]
            }).encode())

    def build_opener(handler):
        assert isinstance(handler, NoCredentialRedirect)
        return FakeOpener()

    monkeypatch.setattr(urllib.request, "build_opener", build_opener)
    monkeypatch.setattr(seo, "reserve_paid_request", lambda *_: None)
    result = seo.gemini_seo("landscape", "lake", "mountain", api_key="seo-test-secret")
    assert result.title == "Original Landscape"
    assert len(captured) == 1
    assert captured[0][0].get_header("X-goog-api-key") == "seo-test-secret"


def test_authenticated_modules_cannot_use_raw_urlopen():
    """Fail if a future provider/SEO module reintroduces a redirectable URL opener.

    The only reviewed direct urlopen is unauthenticated public Trends RSS.
    Any new module wishing to use urlopen must undergo explicit security review.
    """
    root = Path(__file__).resolve().parents[1] / "src" / "podbot"
    safe_public_rss = {"trends.py"}
    violations = []
    for file in sorted(root.glob("*.py")):
        tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        imported_urlopen = any(
            isinstance(node, ast.ImportFrom)
            and node.module == "urllib.request"
            and any(alias.name == "urlopen" for alias in node.names)
            for node in ast.walk(tree)
        )
        calls = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id == "urlopen" and imported_urlopen:
                calls.append(node.lineno)
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "urlopen"
                and isinstance(func.value, ast.Attribute)
                and func.value.attr == "request"
                and isinstance(func.value.value, ast.Name)
                and func.value.value.id == "urllib"
            ):
                calls.append(node.lineno)
        if calls and file.name not in safe_public_rss:
            violations.append(f"{file.name}:{','.join(map(str, calls))}")
    assert not violations, "Raw urlopen outside reviewed public RSS: " + ", ".join(violations)
