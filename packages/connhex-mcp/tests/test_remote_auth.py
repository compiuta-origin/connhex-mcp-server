import logging

import pytest
from connhex_mcp.auth import remote
from connhex_mcp.auth.remote import (
    RENEWAL_IDLE_TTL,
    ConnhexOAuthProvider,
    StoredCredentials,
)
from connhex_mcp.config import MCPSettings
from fastmcp.server.auth.auth import AccessToken


def make_settings() -> MCPSettings:
    return MCPSettings(
        instance_url="https://compiuta.connhex.dev",
        public_url="https://mcp.compiuta.connhex.dev",
    )


def add_renewal_record(
    provider: ConnhexOAuthProvider,
    token: str = "expired-token",
    identifier: str = "user@example.com",
    password: str = "secret",
) -> str:
    return provider._create_renewal_record(
        token, StoredCredentials(identifier, password)
    )


@pytest.mark.asyncio
async def test_load_access_token_auto_renews_when_credentials_are_known(
    monkeypatch: pytest.MonkeyPatch,
):
    provider = ConnhexOAuthProvider(make_settings())
    record_id = add_renewal_record(provider)
    provider._renewal_records[record_id].client_id = "client-1"
    provider._access_tokens["expired-token"] = AccessToken(
        token="expired-token",
        client_id="client-1",
        scopes=[],
        expires_at=10,
    )

    async def fake_get_session_ttl(token: str) -> int | None:
        if token == "expired-token":
            return None
        if token == "renewed-token":
            return 300
        raise AssertionError(f"unexpected token: {token}")

    async def fake_login(
        instance_url: str, identifier: str, password: str
    ) -> str:
        assert instance_url == "https://compiuta.connhex.dev/"
        assert identifier == "user@example.com"
        assert password == "secret"
        return "renewed-token"

    monkeypatch.setattr(remote, "_now", lambda: 1000.0)
    monkeypatch.setattr(provider, "_get_session_ttl", fake_get_session_ttl)
    monkeypatch.setattr(remote, "password_login", fake_login)

    token = await provider.load_access_token("expired-token")

    assert token is not None
    assert token.token == "renewed-token"
    assert token.client_id == "client-1"
    assert provider._token_forwarding["expired-token"] == "renewed-token"
    assert provider._token_records["renewed-token"] == record_id
    assert provider._renewal_records[record_id].current_token == "renewed-token"
    assert provider._renewal_records[record_id].last_used_at == 1000.0
    assert "expired-token" not in provider._access_tokens


@pytest.mark.asyncio
async def test_load_access_token_reuses_forwarded_token_after_renewal(
    monkeypatch: pytest.MonkeyPatch,
):
    provider = ConnhexOAuthProvider(make_settings())
    record_id = add_renewal_record(provider)
    provider._renewal_records[record_id].client_id = "client-1"
    provider._access_tokens["expired-token"] = AccessToken(
        token="expired-token",
        client_id="client-1",
        scopes=[],
        expires_at=10,
    )

    ttl_calls: list[str] = []
    login_calls: list[tuple[str, str, str]] = []
    now = 1000.0

    async def fake_get_session_ttl(token: str) -> int | None:
        ttl_calls.append(token)
        if token == "expired-token":
            return None
        if token == "renewed-token":
            return 300
        raise AssertionError(f"unexpected token: {token}")

    async def fake_login(
        instance_url: str, identifier: str, password: str
    ) -> str:
        login_calls.append((instance_url, identifier, password))
        return "renewed-token"

    monkeypatch.setattr(remote, "_now", lambda: now)
    monkeypatch.setattr(provider, "_get_session_ttl", fake_get_session_ttl)
    monkeypatch.setattr(remote, "password_login", fake_login)

    first = await provider.load_access_token("expired-token")
    second = await provider.load_access_token("expired-token")

    assert first is not None
    assert first.token == "renewed-token"
    assert second is not None
    assert second.token == "renewed-token"
    assert second.client_id == "client-1"
    assert provider._token_forwarding["expired-token"] == "renewed-token"
    assert provider._token_records["expired-token"] == record_id
    assert provider._token_records["renewed-token"] == record_id
    assert provider._access_tokens["renewed-token"].token == "renewed-token"
    assert login_calls == [
        (
            "https://compiuta.connhex.dev/",
            "user@example.com",
            "secret",
        )
    ]
    assert ttl_calls == ["expired-token", "renewed-token"]


@pytest.mark.asyncio
async def test_cleanup_keeps_renewal_state_after_token_expiry_until_idle_ttl(
    monkeypatch: pytest.MonkeyPatch,
):
    provider = ConnhexOAuthProvider(make_settings())
    record_id = add_renewal_record(provider)
    provider._renewal_records[record_id].client_id = "client-1"
    provider._renewal_records[record_id].last_used_at = 1000.0
    provider._access_tokens["expired-token"] = AccessToken(
        token="expired-token",
        client_id="client-1",
        scopes=[],
        expires_at=1010,
    )

    monkeypatch.setattr(remote, "_now", lambda: 1020.0)
    provider._cleanup_once()

    assert "expired-token" not in provider._access_tokens
    assert record_id in provider._renewal_records
    assert provider._token_records["expired-token"] == record_id


@pytest.mark.asyncio
async def test_cleanup_removes_idle_renewal_state(
    monkeypatch: pytest.MonkeyPatch,
):
    provider = ConnhexOAuthProvider(make_settings())
    record_id = add_renewal_record(provider, token="stale-token")
    provider._renewal_records[record_id].client_id = "client-1"
    provider._renewal_records[record_id].last_used_at = 1000.0
    provider._token_forwarding["legacy-token"] = "stale-token"
    provider._token_records["legacy-token"] = record_id
    provider._access_tokens["stale-token"] = AccessToken(
        token="stale-token",
        client_id="client-1",
        scopes=[],
        expires_at=1100,
    )

    monkeypatch.setattr(remote, "_now", lambda: 1000.0 + RENEWAL_IDLE_TTL + 1)
    provider._cleanup_once()

    assert record_id not in provider._renewal_records
    assert "stale-token" not in provider._token_records
    assert "legacy-token" not in provider._token_records
    assert "legacy-token" not in provider._token_forwarding
    assert "stale-token" not in provider._access_tokens


@pytest.mark.asyncio
async def test_revoke_token_clears_local_renewal_state():
    provider = ConnhexOAuthProvider(make_settings())
    record_id = add_renewal_record(provider, token="live-token")
    provider._renewal_records[record_id].client_id = "client-1"
    provider._token_forwarding["old-token"] = "live-token"
    provider._token_records["old-token"] = record_id
    provider._access_tokens["live-token"] = AccessToken(
        token="live-token",
        client_id="client-1",
        scopes=[],
        expires_at=9999,
    )

    await provider.revoke_token("old-token")

    assert record_id not in provider._renewal_records
    assert "live-token" not in provider._token_records
    assert "old-token" not in provider._token_records
    assert "old-token" not in provider._token_forwarding
    assert "live-token" not in provider._access_tokens


@pytest.mark.asyncio
async def test_load_access_token_logs_warning_when_expired_token_has_no_credentials(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    provider = ConnhexOAuthProvider(make_settings())
    provider._access_tokens["expired-token"] = AccessToken(
        token="expired-token",
        client_id="client-1",
        scopes=[],
        expires_at=10,
    )

    async def fake_get_session_ttl(token: str) -> int | None:
        assert token == "expired-token"
        return None

    monkeypatch.setattr(provider, "_get_session_ttl", fake_get_session_ttl)

    with caplog.at_level(logging.WARNING, logger="connhex-mcp"):
        token = await provider.load_access_token("expired-token")

    assert token is None
    assert "expired-token" not in provider._access_tokens
    assert (
        "Access token expired and no credentials available for renewal"
        in caplog.text
    )


@pytest.mark.asyncio
async def test_load_access_token_cannot_renew_token_from_previous_process(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    original_provider = ConnhexOAuthProvider(make_settings())
    add_renewal_record(original_provider, token="old-token")

    restarted_provider = ConnhexOAuthProvider(make_settings())

    async def fake_get_session_ttl(token: str) -> int | None:
        assert token == "old-token"
        return None

    monkeypatch.setattr(
        restarted_provider, "_get_session_ttl", fake_get_session_ttl
    )

    with caplog.at_level(logging.WARNING, logger="connhex-mcp"):
        token = await restarted_provider.load_access_token("old-token")

    assert token is None
    assert "old-token" not in restarted_provider._token_records
    assert (
        "Access token expired and no credentials available for renewal"
        in caplog.text
    )
