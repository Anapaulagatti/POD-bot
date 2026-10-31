"""No live calls: atomic API reservations and explicit OS vault operations."""

import json
import sys
import types

import pytest

from podbot.api_limits import get_daily_limit, reserve_paid_request, set_daily_limit
from podbot.credential_vault import (
    erase_credentials,
    remember_credentials,
    restore_credentials,
)


@pytest.fixture(autouse=True)
def clean_local(monkeypatch, tmp_path):
    monkeypatch.setenv("PODBOT_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("PODBOT_PAID_CALLS_PER_DAY", raising=False)


def test_paid_attempts_are_capped_per_provider_and_persist(tmp_path):
    set_daily_limit(2)
    assert get_daily_limit() == 2
    assert reserve_paid_request("openai", day="2026-10-31") == 1
    assert reserve_paid_request("openai", day="2026-10-31") == 2
    with pytest.raises(PermissionError, match="daily attempt cap"):
        reserve_paid_request("openai", day="2026-10-31")
    assert reserve_paid_request("gemini", day="2026-10-31") == 1
    assert reserve_paid_request("openai", day="2026-11-01") == 1
    assert (tmp_path / "paid_api_attempts.sqlite3").is_file()
    assert "secret" not in (tmp_path / "api_call_limits.json").read_text()


def test_zero_limit_fails_closed_and_invalid_limits_rejected():
    set_daily_limit(0)
    with pytest.raises(PermissionError, match="disabled"):
        reserve_paid_request("gemini")
    for invalid in (-1, 101, "3", True):
        with pytest.raises(ValueError):
            set_daily_limit(invalid)


def test_env_override_and_corrupt_config_fail_closed(monkeypatch, tmp_path):
    set_daily_limit(5)
    monkeypatch.setenv("PODBOT_PAID_CALLS_PER_DAY", "1")
    assert get_daily_limit() == 1
    monkeypatch.setenv("PODBOT_PAID_CALLS_PER_DAY", "wrong")
    with pytest.raises(ValueError):
        reserve_paid_request("openai")
    monkeypatch.delenv("PODBOT_PAID_CALLS_PER_DAY")
    (tmp_path / "api_call_limits.json").write_text('{"invalid":3}')
    with pytest.raises(RuntimeError, match="Fail closed"):
        reserve_paid_request("openai")


def test_credentials_never_saved_without_explicit_confirm():
    with pytest.raises(PermissionError):
        remember_credentials({"OPENAI_API_KEY": "secret"})
    with pytest.raises(PermissionError):
        restore_credentials()
    with pytest.raises(PermissionError):
        erase_credentials()


def test_credential_vault_only_stores_allowlisted_keys(monkeypatch):
    db = {}

    class Backend:
        priority = 1

    fake = types.ModuleType("keyring")
    fake.get_keyring = lambda: Backend()
    fake.set_password = lambda service, user, token: db.__setitem__((service, user), token)
    fake.get_password = lambda service, user: db.get((service, user))
    fake.delete_password = lambda service, user: db.pop((service, user), None)
    monkeypatch.setitem(sys.modules, "keyring", fake)

    stored = remember_credentials(
        {"OPENAI_API_KEY": "demo-token", "CLOUDFLARE_ACCOUNT_ID": "public-account"},
        confirmed=True,
    )
    assert stored == 1
    assert restore_credentials(confirmed=True) == {"OPENAI_API_KEY": "demo-token"}
    assert all("CLOUDFLARE_ACCOUNT_ID" not in key for key in db)
    assert erase_credentials(confirmed=True) == 1
    assert restore_credentials(confirmed=True) == {}


def test_vault_rejects_non_secure_backend(monkeypatch):
    fake = types.ModuleType("keyring")
    fake.get_keyring = lambda: types.SimpleNamespace(priority=0)
    monkeypatch.setitem(sys.modules, "keyring", fake)
    with pytest.raises(RuntimeError, match="vault"):
        restore_credentials(confirmed=True)
