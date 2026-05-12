from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from connhex_cli.main import app
from connhex_cli.auth import store as auth_store

runner = CliRunner()


@pytest.fixture(autouse=True)
def tmp_config(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "connhex_cli.auth.store._creds_path",
        lambda: tmp_path / "connhex" / "credentials.json",
    )


def test_login_writes_credentials():
    fake_token = "ory_st_faketoken"
    fake_expires = (
        datetime.now(timezone.utc) + timedelta(hours=24)
    ).isoformat()

    session_payload = {
        "identity": {"traits": {"email": "user@example.com"}},
        "expires_at": fake_expires,
    }

    with patch(
        "connhex_cli.commands.auth.asyncio.run",
        side_effect=[fake_token, session_payload],
    ):
        result = runner.invoke(
            app,
            [
                "auth",
                "login",
                "--instance-url",
                "https://compiuta.connhex.dev",
                "--username",
                "user@example.com",
                "--password",
                "secret",
            ],
        )

    assert result.exit_code == 0, result.output
    creds = auth_store.load()
    assert creds is not None
    assert creds.token == fake_token
    assert creds.user == "user@example.com"


def test_login_prints_plaintext_warning(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "connhex_cli.auth.store._creds_path",
        lambda: tmp_path / "connhex2" / "credentials.json",
    )

    fake_token = "ory_st_faketoken2"
    fake_expires = (
        datetime.now(timezone.utc) + timedelta(hours=24)
    ).isoformat()

    with patch(
        "connhex_cli.commands.auth.asyncio.run",
        side_effect=[fake_token, {"expires_at": fake_expires}],
    ):
        result = runner.invoke(
            app,
            [
                "auth",
                "login",
                "--instance-url",
                "https://compiuta.connhex.dev",
                "--username",
                "user@example.com",
                "--password",
                "secret",
            ],
        )

    assert result.exit_code == 0, result.output
    assert "plaintext" in result.output
