from collections.abc import Callable

from connhex_sdk.auth.credentials import CredentialsProvider
from connhex_sdk.auth.session import (
    extract_bearer_from_headers,
    extract_token_from_cookie,
)
from connhex_sdk.config import AuthType, CoreSettings

ValidatedTokenGetter = Callable[[], str | None]


class AuthResolver:
    """Resolve per-request auth headers from the available auth sources.

    Framework integrations (e.g. fastmcp's OAuth-validated access tokens) are
    injected as an optional `validated_token_getter`. When `prefer_validated_token`
    is true the getter is consulted before the request's own Bearer header —
    this is what remote OAuth mode needs so the auto-renewed token wins over
    the (potentially expired) one the client originally sent.
    """

    def __init__(
        self,
        settings: CoreSettings,
        *,
        validated_token_getter: ValidatedTokenGetter | None = None,
        prefer_validated_token: bool = False,
    ):
        self.settings = settings
        self._validated_token_getter = validated_token_getter
        self._prefer_validated_token = prefer_validated_token
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

    def _validated_token(self) -> str | None:
        if self._validated_token_getter is None:
            return None
        try:
            return self._validated_token_getter()
        except Exception:
            return None

    async def resolve(self, headers: dict) -> dict[str, str]:
        """Returns headers dict to use for Connhex API calls."""
        if self._prefer_validated_token:
            token = self._validated_token()
            if token:
                return {"Authorization": f"Bearer {token}"}

        bearer = await extract_bearer_from_headers(headers)
        if bearer:
            return {"Authorization": bearer}

        token = self._validated_token()
        if token:
            return {"Authorization": f"Bearer {token}"}

        headers_lower = {k.lower(): v for k, v in headers.items()}
        if headers_lower.get("cookie"):
            cookie_token = await extract_token_from_cookie(
                headers, self.settings.accounts_url
            )
            if cookie_token:
                return {"Authorization": cookie_token}
            return {"Cookie": headers_lower["cookie"]}

        if self.settings.auth_type == AuthType.TOKEN:
            assert self.settings.bearer_token, (
                "CONNHEX_BEARER_TOKEN is required when auth_type is 'token'"
            )
            return {"Authorization": f"Bearer {self.settings.bearer_token}"}

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
