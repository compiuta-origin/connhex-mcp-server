import httpx

from connhex_sdk.auth.resolver import AuthResolver
from connhex_sdk.errors import ConnhexAPIError, raise_for_connhex_response

TIMEOUT = 30.0


class ConnhexClient:
    def __init__(self, settings, auth_resolver: AuthResolver):
        self.settings = settings
        self.auth_resolver = auth_resolver
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(TIMEOUT),
            follow_redirects=True,
        )

    async def request(
        self,
        method: str,
        path: str,
        headers: dict,
        base: str = "apis",
        **kwargs,
    ) -> httpx.Response:
        """
        Make an authenticated request to the Connhex API.
        Handles auth resolution and 401 retry.
        """
        base_url = (
            self.settings.apis_url
            if base == "apis"
            else self.settings.accounts_url
        )
        url = f"{base_url}{path}"

        # Resolve auth from transport headers or server config
        auth_headers = await self.auth_resolver.resolve(headers)

        merged_headers = {
            "Accept": "application/json",
            **auth_headers,
            **kwargs.pop("extra_headers", {}),
        }

        try:
            resp = await self._http.request(
                method, url, headers=merged_headers, **kwargs
            )

            # 401 retry: only works for credentials provider
            if resp.status_code == 401:
                new_auth = await self.auth_resolver.handle_401()
                if new_auth:
                    merged_headers.update(new_auth)
                    resp = await self._http.request(
                        method, url, headers=merged_headers, **kwargs
                    )

            # Raise structured error on failure
            raise_for_connhex_response(resp)
            return resp
        except httpx.RequestError as e:
            # Wrap network-level errors
            raise ConnhexAPIError(status=0, detail=f"Network error: {str(e)}")

    async def close(self):
        await self._http.aclose()
