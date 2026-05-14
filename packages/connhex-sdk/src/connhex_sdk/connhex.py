import os

from connhex_sdk.client import (
    MAX_RETRIES,
    TIMEOUT,
    ConnhexClient,
    TokenProvider,
)
from connhex_sdk.iam import IAMService
from connhex_sdk.models import ModelsService
from connhex_sdk.provision import ProvisionService
from connhex_sdk.reader import ReaderService
from connhex_sdk.resources import ResourcesService
from connhex_sdk.rules_engine import RulesEngineService
from connhex_sdk.things import ThingsService

ENV_INSTANCE_URL = "CONNHEX_INSTANCE_URL"
ENV_TOKEN = "CONNHEX_BEARER_TOKEN"


class AsyncConnhex:
    """Async client for the Connhex API.

    This is the entry point of the SDK. One `AsyncConnhex` instance owns a
    single underlying HTTP client and exposes every Connhex service as an
    attribute:

        ```python
        from connhex_sdk import AsyncConnhex

        async with AsyncConnhex(
            instance_url="https://your-tenant.connhex.com",
            token="<personal access token>",
        ) as connhex:
            me = await connhex.iam.whoami()
            things = await connhex.things.list(limit=20)
            thing = await connhex.things.get("thing-id")
        ```

    Authentication. Pass exactly one of:

    - `token`: a static bearer token (personal access token). If omitted,
      the `CONNHEX_BEARER_TOKEN` environment variable is used.
    - `token_provider`: an async callable returning a fresh token on every
      request — for multi-user servers or short-lived tokens.

    `instance_url` falls back to the `CONNHEX_INSTANCE_URL` environment
    variable when omitted.

    Lifecycle. Always close the client to release the underlying connection
    pool. The recommended form is `async with AsyncConnhex(...) as c: ...`;
    if you can't use a context manager, call `await c.close()` explicitly.

    Retries. Transient failures (network errors, HTTP 408/429/5xx) are
    retried with exponential backoff and jitter, honoring `Retry-After` when
    the server sends it. Set `max_retries=0` to disable.

    Args:
        instance_url: Base URL of your Connhex tenant, e.g.
            `"https://your-tenant.connhex.com"`. Falls back to
            `$CONNHEX_INSTANCE_URL`.
        token: Static bearer token. Falls back to `$CONNHEX_BEARER_TOKEN`.
            Mutually exclusive with `token_provider`.
        token_provider: Async callable resolving a bearer token per request.
            Mutually exclusive with `token`.
        timeout: Default per-request timeout in seconds.
        max_retries: Max retries for transient failures (0 disables).
    """

    def __init__(
        self,
        *,
        instance_url: str | None = None,
        token: str | None = None,
        token_provider: TokenProvider | None = None,
        timeout: float = TIMEOUT,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        instance_url = instance_url or os.environ.get(ENV_INSTANCE_URL)
        if not instance_url:
            raise ValueError(
                "instance_url is required "
                f"(pass it explicitly or set ${ENV_INSTANCE_URL})"
            )
        if token is None and token_provider is None:
            token = os.environ.get(ENV_TOKEN)

        self._http = ConnhexClient(
            instance_url=instance_url,
            token=token,
            token_provider=token_provider,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.things = ThingsService(self._http)
        self.models = ModelsService(self._http)
        self.rules = RulesEngineService(self._http)
        self.iam = IAMService(self._http)
        self.reader = ReaderService(self._http)
        self.provision = ProvisionService(self._http)
        self.resources = ResourcesService(self._http, "resources")
        self.manufacturing = ResourcesService(self._http, "manufacturing")

    async def close(self) -> None:
        await self._http.close()

    async def __aenter__(self) -> "AsyncConnhex":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()
