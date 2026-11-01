"""Fail-closed transport for authenticated provider requests.

Provider tokens must never follow redirects to a different origin.
"""
from __future__ import annotations

import urllib.parse
import urllib.request

APPROVED_API_HOSTS = frozenset({
    "api.openai.com",
    "generativelanguage.googleapis.com",
    "api.replicate.com",
    "fal.run",
    "api.stability.ai",
    "api.cloudflare.com",
    "gen.pollinations.ai",
})


class NoCredentialRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise RuntimeError(
            "Authenticated provider redirected this request; stopped to protect API credentials."
        )


def open_authenticated(request: urllib.request.Request, *, timeout: int):
    """Open only first-party HTTPS API origins, with redirects disabled.

    The caller owns the returned response and must close it.
    """
    parsed = urllib.parse.urlsplit(request.full_url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in APPROVED_API_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
        or parsed.fragment
    ):
        raise ValueError("Authenticated provider request has an unapproved destination.")
    return urllib.request.build_opener(NoCredentialRedirect()).open(
        request, timeout=timeout
    )
