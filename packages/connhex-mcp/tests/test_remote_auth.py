import logging
import sqlite3

import pytest
from connhex.urls import DEFAULT_INSTANCE_URL
from connhex_mcp.auth import remote
from connhex_mcp.auth.remote import (
    RENEWAL_IDLE_TTL,
    ConnhexOAuthProvider,
    StoredCredentials,
)
from connhex_mcp.config import MCPSettings
from fastmcp.server.auth.auth import AccessToken
from mcp.shared.auth import OAuthClientInformationFull
from starlette.applications import Starlette
from starlette.testclient import TestClient


def make_settings(
    openai_apps_challenge_token: str | None = None,
    oauth_client_store_path: str | None = None,
) -> MCPSettings:
    return MCPSettings(
        instance_url="https://compiuta.connhex.dev",
        public_url="https://mcp.compiuta.connhex.dev",
        openai_apps_challenge_token=openai_apps_challenge_token,
        oauth_client_store_path=oauth_client_store_path,
    )


def test_settings_default_to_saas_instance_url(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("CONNHEX_INSTANCE_URL", raising=False)

    settings = MCPSettings()

    assert str(settings.instance_url).rstrip("/") == DEFAULT_INSTANCE_URL


def test_openai_apps_challenge_route_is_absent_without_token():
    provider = ConnhexOAuthProvider(make_settings())
    routes = provider.get_routes("/")

    assert all(
        route.path != "/.well-known/openai-apps-challenge" for route in routes
    )


def test_openai_apps_challenge_route_returns_configured_token():
    provider = ConnhexOAuthProvider(make_settings("challenge-token"))
    app = Starlette(routes=provider.get_routes("/"))
    client = TestClient(app, raise_server_exceptions=True)

    response = client.get("/.well-known/openai-apps-challenge")

    assert response.status_code == 200
    assert response.text == "challenge-token"
    assert response.headers["content-type"].startswith("text/plain")


def make_oauth_client(
    client_id: str = "client-1",
) -> OAuthClientInformationFull:
    return OAuthClientInformationFull(
        client_id=client_id,
        client_secret="client-secret",
        client_id_issued_at=1_717_171_717,
        client_secret_expires_at=None,
        redirect_uris=["https://chatgpt.com/connector/oauth/test"],
        token_endpoint_auth_method="client_secret_post",
        grant_types=["authorization_code", "refresh_token"],
        response_types=["code"],
        scope="",
        client_name="ChatGPT",
    )


@pytest.mark.asyncio
async def test_register_client_uses_memory_when_store_path_is_unset():
    provider = ConnhexOAuthProvider(make_settings())
    client_info = make_oauth_client()

    await provider.register_client(client_info)

    assert await provider.get_client("client-1") == client_info


@pytest.mark.asyncio
async def test_sqlite_store_persists_registered_clients_after_restart(
    tmp_path,
):
    db_path = tmp_path / "oauth-clients.sqlite"
    first_provider = ConnhexOAuthProvider(
        make_settings(oauth_client_store_path=str(db_path))
    )
    client_info = make_oauth_client()

    await first_provider.register_client(client_info)

    restarted_provider = ConnhexOAuthProvider(
        make_settings(oauth_client_store_path=str(db_path))
    )

    persisted = await restarted_provider.get_client("client-1")
    assert persisted == client_info
    assert persisted is not None
    assert persisted.client_secret == "client-secret"
    assert persisted.token_endpoint_auth_method == "client_secret_post"
    assert persisted.redirect_uris == client_info.redirect_uris
    assert persisted.grant_types == ["authorization_code", "refresh_token"]
    assert persisted.response_types == ["code"]
    assert persisted.client_id_issued_at == 1_717_171_717


@pytest.mark.asyncio
async def test_authorize_accepts_persisted_client_after_restart(tmp_path):
    db_path = tmp_path / "oauth-clients.sqlite"
    first_provider = ConnhexOAuthProvider(
        make_settings(oauth_client_store_path=str(db_path))
    )
    await first_provider.register_client(make_oauth_client())

    restarted_provider = ConnhexOAuthProvider(
        make_settings(oauth_client_store_path=str(db_path))
    )
    app = Starlette(routes=restarted_provider.get_routes("/"))
    client = TestClient(app, raise_server_exceptions=True)

    response = client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": "client-1",
            "redirect_uri": "https://chatgpt.com/connector/oauth/test",
            "code_challenge": "challenge",
            "code_challenge_method": "S256",
            "state": "state-1",
            "resource": "https://mcp.compiuta.connhex.dev/",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["location"].startswith(
        "https://mcp.compiuta.connhex.dev/oauth/login?flow_id="
    )


def test_authorize_rejects_unknown_client(tmp_path):
    provider = ConnhexOAuthProvider(
        make_settings(
            oauth_client_store_path=str(tmp_path / "oauth-clients.sqlite")
        )
    )
    app = Starlette(routes=provider.get_routes("/"))
    client = TestClient(app, raise_server_exceptions=True)

    response = client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": "unknown-client",
            "redirect_uri": "https://chatgpt.com/connector/oauth/test",
            "code_challenge": "challenge",
            "code_challenge_method": "S256",
            "state": "state-1",
            "resource": "https://mcp.compiuta.connhex.dev/",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "invalid_request",
        "error_description": "Client ID 'unknown-client' not found",
        "state": "state-1",
    }


@pytest.mark.asyncio
async def test_sqlite_store_ignores_corrupt_client_rows(
    tmp_path, caplog: pytest.LogCaptureFixture
):
    db_path = tmp_path / "oauth-clients.sqlite"
    ConnhexOAuthProvider(make_settings(oauth_client_store_path=str(db_path)))
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO oauth_clients (
                client_id,
                client_info,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?)
            """,
            ("bad-client", "{not-json", 1, 1),
        )

    provider = ConnhexOAuthProvider(
        make_settings(oauth_client_store_path=str(db_path))
    )

    with caplog.at_level(logging.WARNING, logger=remote.logger.name):
        client_info = await provider.get_client("bad-client")

    assert client_info is None
    assert "Ignoring invalid persisted OAuth client bad-client" in caplog.text


def test_sqlite_store_requires_existing_parent_directory(tmp_path):
    missing_path = tmp_path / "missing" / "oauth-clients.sqlite"

    with pytest.raises(ValueError, match="does not exist"):
        ConnhexOAuthProvider(
            make_settings(oauth_client_store_path=str(missing_path))
        )


def test_sqlite_store_rejects_unusable_database_path(tmp_path):
    with pytest.raises(ValueError, match="Unable to initialize"):
        ConnhexOAuthProvider(
            make_settings(oauth_client_store_path=str(tmp_path))
        )


@pytest.mark.asyncio
async def test_sqlite_store_does_not_persist_user_credentials(tmp_path):
    db_path = tmp_path / "oauth-clients.sqlite"
    provider = ConnhexOAuthProvider(
        make_settings(oauth_client_store_path=str(db_path))
    )

    add_renewal_record(
        provider,
        token="session-token",
        identifier="private@example.com",
        password="user-password",
    )
    await provider.register_client(make_oauth_client())

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT client_info FROM oauth_clients").fetchall()

    stored_payload = "\n".join(row[0] for row in rows)
    assert "private@example.com" not in stored_payload
    assert "user-password" not in stored_payload


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
