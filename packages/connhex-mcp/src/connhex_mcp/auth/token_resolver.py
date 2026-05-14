from collections.abc import Awaitable, Callable

from connhex.urls import build_accounts_url
from fastmcp.server.dependencies import get_access_token, get_http_headers

from connhex_mcp.auth.credentials import CredentialsProvider
from connhex_mcp.auth.session import (
    extract_bearer_from_headers,
    extract_token_from_cookie,
)
from connhex_mcp.config import MCPSettings


def _fastmcp_validated_token() -> str | None:
    """Return the fastmcp-validated OAuth access token, if any."""
    try:
        access_token = get_access_token()
    except Exception:
        return None
    if access_token and access_token.token:
        return access_token.token
    return None


def build_token_provider(
    settings: MCPSettings,
) -> Callable[[], Awaitable[str]]:
    """Build a per-request token provider for this MCP server.

    Priority:
      1. In remote mode, prefer the fastmcp-validated (auto-renewed) token.
      2. Bearer token from the incoming request's Authorization header.
      3. fastmcp-validated token (as fallback in local mode).
      4. Session cookie exchanged via Kratos whoami.
      5. Static `bearer_token` from settings.
      6. Username/password credentials (auto-refreshing).
    """
    accounts_url = build_accounts_url(str(settings.instance_url))
    creds = (
        CredentialsProvider(accounts_url, settings.username, settings.password)
        if settings.username and settings.password
        else None
    )
    prefer_validated = settings.public_url is not None

    async def resolve() -> str:
        if prefer_validated:
            tok = _fastmcp_validated_token()
            if tok:
                return tok

        headers = get_http_headers() or {}
        bearer = await extract_bearer_from_headers(headers)
        if bearer:
            return bearer.removeprefix("Bearer ").strip()

        tok = _fastmcp_validated_token()
        if tok:
            return tok

        cookie_token = await extract_token_from_cookie(headers, accounts_url)
        if cookie_token:
            return cookie_token.removeprefix("Bearer ").strip()

        if settings.bearer_token:
            return settings.bearer_token

        if creds is not None:
            return await creds.get_token()

        raise RuntimeError(
            "No authentication available for this MCP request. "
            "Configure credentials, a token, or ensure session headers "
            "are forwarded."
        )

    return resolve
