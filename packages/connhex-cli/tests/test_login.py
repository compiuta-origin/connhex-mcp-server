from datetime import datetime, timedelta, timezone

import httpx
import pytest
from connhex_cli.auth import store as auth_store
from connhex_cli.commands import auth as auth_cmd
from connhex_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture(autouse=True)
def tmp_config(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "connhex_cli.auth.store._creds_path",
        lambda: tmp_path / "connhex" / "credentials.json",
    )


def _install_fakes(monkeypatch, token: str, session: dict) -> None:
    monkeypatch.setattr(auth_cmd, "password_login", lambda url, u, p: token)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/auth/sessions/whoami"
        return httpx.Response(200, json=session)

    real_client = httpx.Client

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(auth_cmd.httpx, "Client", factory)


def test_login_writes_credentials(monkeypatch):
    fake_token = "ory_st_faketoken"
    fake_expires = (
        datetime.now(timezone.utc) + timedelta(hours=24)
    ).isoformat()

    _install_fakes(
        monkeypatch,
        fake_token,
        {
            "identity": {"traits": {"email": "user@example.com"}},
            "expires_at": fake_expires,
        },
    )

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

    _install_fakes(monkeypatch, fake_token, {"expires_at": fake_expires})

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
