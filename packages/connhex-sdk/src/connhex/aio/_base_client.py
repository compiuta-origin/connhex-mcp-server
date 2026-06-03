import random
from asyncio import sleep as _sleep
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Awaitable, Callable

import httpx

from connhex import __version__
from connhex.errors import (
    APIConnectionError,
    APITimeoutError,
    raise_for_connhex_response,
)
from connhex.urls import build_url

TIMEOUT = 30.0
MAX_RETRIES = 2
RETRY_INITIAL = 0.5
RETRY_CAP = 8.0
RETRY_JITTER = 0.25
RETRY_STATUSES = frozenset({408, 429, 500, 502, 503, 504})

TokenProvider = Callable[[], Awaitable[str]]


def _retry_after_seconds(resp: httpx.Response) -> float | None:
    """Parse a Retry-After header. Returns None if absent or unparseable."""
    value = resp.headers.get("Retry-After")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(value)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
    except (TypeError, ValueError):
        return None


class ConnhexClient:
    """HTTP client for the Connhex API.

    Auth is provided either as a static `token` or, for callers that need
    per-request token resolution (e.g. multi-user servers), a
    `token_provider` callable invoked on every request.

    Transient failures (network errors and HTTP 429/5xx) are retried with
    exponential backoff + jitter, honoring `Retry-After` when present.
    Set `max_retries=0` to disable retries.
    """

    def __init__(
        self,
        *,
        instance_url: str,
        token: str | None = None,
        token_provider: TokenProvider | None = None,
        timeout: float = TIMEOUT,
        max_retries: int = MAX_RETRIES,
        retry_initial: float = RETRY_INITIAL,
        retry_cap: float = RETRY_CAP,
    ):
        if (token is None) == (token_provider is None):
            raise ValueError(
                "exactly one of `token` or `token_provider` is required"
            )
        self.instance_url = instance_url.rstrip("/")
        self._token = token
        self._token_provider = token_provider
        self._max_retries = max_retries
        self._retry_initial = retry_initial
        self._retry_cap = retry_cap
        self._user_agent = (
            f"connhex-python/{__version__} httpx/{httpx.__version__}"
        )
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
        )

    async def _token_value(self) -> str:
        if self._token_provider is not None:
            return await self._token_provider()
        assert self._token is not None
        return self._token

    def _backoff(self, attempt: int) -> float:
        delay = min(self._retry_initial * (2**attempt), self._retry_cap)
        return delay + random.uniform(0, RETRY_JITTER)

    async def request(
        self,
        method: str,
        path: str,
        *,
        base: str = "apis",
        extra_headers: dict[str, str] | None = None,
        timeout: float | None = None,
        **kwargs,
    ) -> httpx.Response:
        url = f"{build_url(self.instance_url, base)}{path}"
        token = await self._token_value()
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": self._user_agent,
            **(extra_headers or {}),
        }
        if timeout is not None:
            kwargs["timeout"] = httpx.Timeout(timeout)

        for attempt in range(self._max_retries + 1):
            try:
                resp = await self._http.request(
                    method, url, headers=headers, **kwargs
                )
            except httpx.TimeoutException as e:
                if attempt == self._max_retries:
                    raise APITimeoutError(
                        f"Request timed out: {e}", cause=e
                    ) from e
                await _sleep(self._backoff(attempt))
                continue
            except httpx.RequestError as e:
                if attempt == self._max_retries:
                    raise APIConnectionError(
                        f"Network error: {e}", cause=e
                    ) from e
                await _sleep(self._backoff(attempt))
                continue

            if (
                resp.status_code in RETRY_STATUSES
                and attempt < self._max_retries
            ):
                delay = _retry_after_seconds(resp)
                if delay is None:
                    delay = self._backoff(attempt)
                await _sleep(delay)
                continue

            raise_for_connhex_response(resp)
            return resp

        # Unreachable: loop always returns or raises.
        raise APIConnectionError("retry loop exhausted")

    async def close(self) -> None:
        await self._http.aclose()
