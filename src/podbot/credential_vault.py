"""Explicit, optional OS keyring storage for selected API credentials only."""

from __future__ import annotations

SERVICE = "PODBotStudio.API"
FIELDS = {
    "CLOUDFLARE_API_TOKEN", "HF_TOKEN", "GEMINI_API_KEY",
    "OPENAI_API_KEY", "REPLICATE_API_TOKEN", "FAL_KEY",
    "STABILITY_API_KEY", "POLLINATIONS_API_KEY",
}


def _keyring():
    try:
        import keyring
    except ImportError as exc:
        raise RuntimeError("Install keyring (included in Windows desktop build).") from exc
    try:
        backend = keyring.get_keyring()
        if getattr(backend, "priority", 0) <= 0:
            raise RuntimeError("No secure OS keyring backend is available on this machine.")
    except Exception as exc:
        raise RuntimeError("Could not access OS credential vault.") from exc
    return keyring


def remember_credentials(values: dict[str, str], *, confirmed: bool = False) -> int:
    if not confirmed:
        raise PermissionError("Explicit consent is required to persist API credentials.")
    ring = _keyring()
    count = 0
    for name, value in values.items():
        if name not in FIELDS:
            continue
        if value.strip():
            ring.set_password(SERVICE, name, value.strip())
            count += 1
    return count


def restore_credentials(*, confirmed: bool = False) -> dict[str, str]:
    if not confirmed:
        raise PermissionError("Restoring API keys requires explicit user action.")
    ring = _keyring()
    return {name: secret for name in sorted(FIELDS)
            if (secret := ring.get_password(SERVICE, name))}


def erase_credentials(*, confirmed: bool = False) -> int:
    if not confirmed:
        raise PermissionError("Deleting stored API keys requires explicit confirmation.")
    ring = _keyring()
    count = 0
    for name in sorted(FIELDS):
        if ring.get_password(SERVICE, name):
            ring.delete_password(SERVICE, name)
            count += 1
    return count
