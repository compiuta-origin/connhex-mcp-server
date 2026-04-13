import time

from connhex_mcp.client import ConnhexClient
from connhex_mcp.utils.jsonapi import build_filter_params

_SCHEMA_TTL_SECONDS = 7 * 24 * 3600
_DEFAULT_HEADERS = {"Accept": "application/vnd.api+json"}


class ResourcesService:
    def __init__(self, client: ConnhexClient, base_url: str):
        self.base_url = base_url
        self.client = client
        self._schema_cache: tuple[float, dict] | None = None
        self._schema_ttl: float = _SCHEMA_TTL_SECONDS

    async def get_schema(self, headers: dict) -> dict:
        """
        Fetch the resource schema for this service. Cached per instance with a
        long TTL (schemas are not expected to change while the service is live).
        """
        cached = self._schema_cache
        if (
            cached is not None
            and (time.monotonic() - cached[0]) < self._schema_ttl
        ):
            return cached[1]
        resp = await self.client.request(
            "GET",
            f"/{self.base_url}/schema",
            headers,
            extra_headers=_DEFAULT_HEADERS,
        )
        data = resp.json()

        self._schema_cache = (time.monotonic(), data)
        return data

    async def list(
        self,
        resource_type: str,
        headers: dict,
        *,
        filter: dict | None = None,
        sort: str | None = None,
        include: str | None = None,
        fields: dict | None = None,
        page_limit: int = 25,
        page_offset: int = 0,
    ) -> dict:
        params: dict = {
            "page[limit]": page_limit,
            "page[offset]": page_offset,
        }
        if sort:
            params["sort"] = sort
        if include:
            params["include"] = include
        if fields:
            for type_name, field_list in fields.items():
                params[f"fields[{type_name}]"] = field_list
        if filter:
            params.update(build_filter_params(filter))

        resp = await self.client.request(
            "GET",
            f"/{self.base_url}/{resource_type}/",
            headers,
            params=params,
            extra_headers=_DEFAULT_HEADERS,
        )
        return resp.json()

    async def get(
        self,
        resource_type: str,
        ids: str,
        headers: dict,
        include: str | None = None,
    ) -> dict:
        params = {}
        if include:
            params["include"] = include
        resp = await self.client.request(
            "GET",
            f"/{self.base_url}/{resource_type}/{ids}/",
            headers,
            params=params,
            extra_headers=_DEFAULT_HEADERS,
        )
        return resp.json()

    async def create(
        self, resource_type: str, data: dict, headers: dict
    ) -> dict:
        resp = await self.client.request(
            "POST",
            f"/{self.base_url}/{resource_type}/",
            headers,
            json=data,
            extra_headers={
                "Content-Type": "application/vnd.api+json",
                **_DEFAULT_HEADERS,
            },
        )
        return resp.json()

    async def update(
        self, resource_type: str, ids: str, data: dict, headers: dict
    ) -> dict:
        resp = await self.client.request(
            "PATCH",
            f"/{self.base_url}/{resource_type}/{ids}/",
            headers,
            json=data,
            extra_headers={
                "Content-Type": "application/vnd.api+json",
                **_DEFAULT_HEADERS,
            },
        )
        return resp.json()

    async def delete(self, resource_type: str, ids: str, headers: dict) -> None:
        await self.client.request(
            "DELETE", f"/{self.base_url}/{resource_type}/{ids}/", headers
        )
