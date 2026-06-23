import pytest
from connhex import BearerAuth, SessionCookieAuth

from connhex_mcp.auth import token_resolver
from connhex_mcp.config import MCPSettings


def settings(**kwargs) -> MCPSettings:
    return MCPSettings(instance_url="https://example.test", **kwargs)


def test_extract_session_cookie_ignores_unrelated_cookies():
    value = token_resolver.extract_session_cookie(
        {
            "Cookie": "csrf_token=csrf-value; chx_auth_session=session-value; other=value"
        }
    )

    assert value == "session-value"


@pytest.mark.asyncio
async def test_auth_provider_uses_incoming_session_cookie(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        token_resolver,
        "get_http_headers",
        lambda: {"Cookie": "other=value; chx_auth_session=session-value"},
    )
    monkeypatch.setattr(
        token_resolver, "_fastmcp_validated_token", lambda: None
    )

    auth = await token_resolver.build_auth_provider(settings())()

    assert auth == SessionCookieAuth("session-value")


@pytest.mark.asyncio
async def test_auth_provider_prefers_bearer_over_session_cookie(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(
        token_resolver,
        "get_http_headers",
        lambda: {
            "Authorization": "Bearer incoming-token",
            "Cookie": "chx_auth_session=session-value",
        },
    )
    monkeypatch.setattr(
        token_resolver, "_fastmcp_validated_token", lambda: None
    )

    auth = await token_resolver.build_auth_provider(settings())()

    assert auth == BearerAuth("incoming-token")


@pytest.mark.asyncio
async def test_auth_provider_uses_configured_session_cookie(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(token_resolver, "get_http_headers", lambda: {})
    monkeypatch.setattr(
        token_resolver, "_fastmcp_validated_token", lambda: None
    )

    auth = await token_resolver.build_auth_provider(
        settings(session_cookie="configured-session")
    )()

    assert auth == SessionCookieAuth("configured-session")
