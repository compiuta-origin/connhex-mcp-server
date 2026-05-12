import os
import stat
import sys
from datetime import datetime, timedelta, timezone

import pytest

from connhex_cli.auth.models import StoredCreds
from connhex_cli.auth import store as auth_store


@pytest.fixture(autouse=True)
def tmp_config(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "connhex_cli.auth.store._creds_path",
        lambda: tmp_path / "connhex" / "credentials.json",
    )
    return tmp_path


def _make_creds(**kwargs) -> StoredCreds:
    defaults = {
        "instance_url": "https://compiuta.connhex.dev",
        "user": "test@example.com",
        "token": "ory_st_abc123",
        "expires_at": (
            datetime.now(timezone.utc) + timedelta(hours=24)
        ).isoformat(),
    }
    defaults.update(kwargs)
    return StoredCreds(**defaults)


def test_round_trip():
    creds = _make_creds()
    auth_store.save(creds)
    loaded = auth_store.load()
    assert loaded is not None
    assert loaded.token == creds.token
    assert loaded.user == creds.user
    assert loaded.instance_url == creds.instance_url


def test_file_permissions():
    if sys.platform == "win32":
        pytest.skip("POSIX permissions not applicable on Windows")
    creds = _make_creds()
    path = auth_store.save(creds)
    mode = stat.S_IMODE(os.stat(path).st_mode)
    assert mode == (stat.S_IRUSR | stat.S_IWUSR)


def test_load_returns_none_when_absent():
    assert auth_store.load() is None


def test_clear():
    creds = _make_creds()
    auth_store.save(creds)
    assert auth_store.load() is not None
    result = auth_store.clear()
    assert result is True
    assert auth_store.load() is None


def test_clear_idempotent():
    assert auth_store.clear() is False


def test_expiry_parsing():
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    creds = _make_creds(expires_at=future)
    auth_store.save(creds)
    loaded = auth_store.load()
    assert loaded is not None
    expires_at = datetime.fromisoformat(loaded.expires_at)
    assert expires_at > datetime.now(timezone.utc)
