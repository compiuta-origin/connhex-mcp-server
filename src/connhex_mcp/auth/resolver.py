from fastmcp.server.dependencies import get_access_token

from connhex_mcp.auth.credentials import CredentialsProvider
from connhex_mcp.auth.session import (
    extract_bearer_from_headers,
    extract_token_from_cookie,
)
from connhex_mcp.config import AuthType, Settings


class AuthResolver:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._credentials_provider: CredentialsProvider | None = None

        if settings.auth_type == AuthType.CREDENTIALS:
            assert settings.username and settings.password, (
                "CONNHEX_USERNAME and CONNHEX_PASSWORD are required "
                "when auth_type is 'credentials'"
            )
            self._credentials_provider = CredentialsProvider(
                accounts_url=settings.accounts_url,
                username=settings.username,
                password=settings.password,
            )

    async def resolve(self, headers: dict) -> dict[str, str]:
        """
        Returns headers dict to use for Connhex API calls.
        """
        # Bearer token from transport headers
        bearer = await extract_bearer_from_headers(headers)
        if bearer:
            return {"Authorization": bearer}

        # OAuth access token injected by fastmcp after token validation
        try:
            access_token = get_access_token()
            if access_token and access_token.token:
                return {"Authorization": f"Bearer {access_token.token}"}
        except Exception:
            pass

        # Cookie from transport headers
        headers_lower = {k.lower(): v for k, v in headers.items()}
        if headers_lower.get("cookie"):
            token = await extract_token_from_cookie(
                headers, self.settings.accounts_url
            )
            if token:
                return {"Authorization": token}
            return {"Cookie": headers_lower["cookie"]}

        # Static token from config
        if self.settings.auth_type == AuthType.TOKEN:
            assert self.settings.bearer_token, (
                "CONNHEX_BEARER_TOKEN is required when auth_type is 'token'"
            )
            return {"Authorization": f"Bearer {self.settings.bearer_token}"}

        # Credentials login
        if self._credentials_provider:
            token = await self._credentials_provider.get_token()
            return {"Authorization": f"Bearer {token}"}

        raise RuntimeError(
            "No authentication available. Configure credentials, "
            "a token, or ensure session headers are forwarded."
        )

    async def handle_401(self) -> dict[str, str] | None:
        if self._credentials_provider:
            token = await self._credentials_provider.refresh_token()
            return {"Authorization": f"Bearer {token}"}
        return None
