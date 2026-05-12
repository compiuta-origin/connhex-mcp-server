from typing import Awaitable, Callable

import httpx

from connhex_sdk.errors import ConnhexAPIError, raise_for_connhex_response
from connhex_sdk.urls import base_url

TIMEOUT = 30.0

TokenProvider = Callable[[], Awaitable[str]]


class ConnhexClient:
    """Thin HTTP client for the Connhex API.

    Auth is provided either as a static `token` or, for callers that need
    per-request token resolution (e.g. multi-user servers), an async
    `token_provider` callable invoked on every request.
    """

    def __init__(
        self,
        *,
        instance_url: str,
        token: str | None = None,
        token_provider: TokenProvider | None = None,
        timeout: float = TIMEOUT,
    ):
        if (token is None) == (token_provider is None):
            raise ValueError(
                "exactly one of `token` or `token_provider` is required"
            )
        self.instance_url = instance_url.rstrip("/")
        self._token = token
        self._token_provider = token_provider
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
        )

    async def _token_value(self) -> str:
        if self._token_provider is not None:
            return await self._token_provider()
        assert self._token is not None
        return self._token

    async def request(
        self,
        method: str,
        path: str,
        *,
        base: str = "apis",
        extra_headers: dict[str, str] | None = None,
        **kwargs,
    ) -> httpx.Response:
        url = f"{base_url(self.instance_url, base)}{path}"
        token = await self._token_value()
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            **(extra_headers or {}),
        }
        try:
            resp = await self._http.request(
                method, url, headers=headers, **kwargs
            )
            raise_for_connhex_response(resp)
            return resp
        except httpx.RequestError as e:
            raise ConnhexAPIError(status=0, detail=f"Network error: {e}")

    async def close(self) -> None:
        await self._http.aclose()
