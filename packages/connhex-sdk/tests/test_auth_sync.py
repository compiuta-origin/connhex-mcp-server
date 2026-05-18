"""Tests for the sync password_login helper."""

import httpx
import pytest
from connhex.sync import auth as sync_auth
from connhex.sync.auth import password_login


def _install_transport(monkeypatch, handler):
    """Patch httpx.Client to use a MockTransport with `handler`."""
    real_client = httpx.Client

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(sync_auth.httpx, "Client", factory)


def test_password_login_success(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth/self-service/login/api":
            return httpx.Response(
                200,
                json={
                    "ui": {
                        "action": "https://accounts.example.test/auth/login/submit",
                    }
                },
            )
        assert request.url.path == "/auth/login/submit"
        return httpx.Response(200, json={"session_token": "ory_st_abc"})

    _install_transport(monkeypatch, handler)
    token = password_login("https://example.test", "user@example.com", "secret")
    assert token == "ory_st_abc"


def test_password_login_invalid_credentials(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/auth/self-service/login/api":
            return httpx.Response(
                200,
                json={
                    "ui": {
                        "action": "https://accounts.example.test/auth/login/submit",
                    }
                },
            )
        return httpx.Response(
            400,
            json={
                "ui": {
                    "messages": [
                        {"text": "The provided credentials are invalid"}
                    ]
                }
            },
        )

    _install_transport(monkeypatch, handler)
    with pytest.raises(ValueError, match="invalid"):
        password_login("https://example.test", "user", "wrong")
