from __future__ import annotations

from connhex_sdk.client import ConnhexClient
from connhex_sdk.things.schemas import (
    BatchStatusRes,
    ChannelsPage,
    FlappingResponse,
    StatusSummary,
    Thing,
    ThingsPage,
    UptimeResponse,
)


class ThingsService:
    def __init__(self, client: ConnhexClient):
        self.client = client

    async def get(self, thing_id: str, headers: dict) -> Thing:
        resp = await self.client.request(
            "GET", f"/iot/things/{thing_id}", headers
        )
        return Thing.model_validate(resp.json())

    async def list(
        self,
        headers: dict,
        *,
        limit: int = 10,
        offset: int = 0,
        name: str | None = None,
        order: str | None = None,
        dir: str | None = None,
    ) -> ThingsPage:
        params: dict = {"limit": limit, "offset": offset}
        if name is not None:
            params["name"] = name
        if order is not None:
            params["order"] = order
        if dir is not None:
            params["dir"] = dir
        resp = await self.client.request(
            "GET", "/iot/things", headers, params=params
        )
        return ThingsPage.model_validate(resp.json())

    async def get_status(self, ids: list[str], headers: dict) -> BatchStatusRes:
        resp = await self.client.request(
            "POST",
            "/iot/things/status",
            headers,
            json={"ids": ids},
            extra_headers={"Content-Type": "application/json"},
        )
        return BatchStatusRes.model_validate(resp.json())

    async def get_status_summary(self, headers: dict) -> StatusSummary:
        resp = await self.client.request(
            "GET", "/iot/things/status/summary", headers
        )
        return StatusSummary.model_validate(resp.json())

    async def get_flapping(
        self,
        headers: dict,
        *,
        window: str | None = None,
        min_reconnects: int | None = None,
        limit: int | None = None,
    ) -> FlappingResponse:
        params: dict = {}
        if window is not None:
            params["window"] = window
        if min_reconnects is not None:
            params["min"] = min_reconnects
        if limit is not None:
            params["limit"] = limit
        resp = await self.client.request(
            "GET", "/iot/things/status/flapping", headers, params=params
        )
        return FlappingResponse.model_validate(resp.json())

    async def get_uptime(
        self,
        thing_id: str,
        headers: dict,
        *,
        from_ts: int | None = None,
        to_ts: int | None = None,
    ) -> UptimeResponse:
        params: dict = {}
        if from_ts is not None:
            params["from"] = from_ts
        if to_ts is not None:
            params["to"] = to_ts
        resp = await self.client.request(
            "GET", f"/iot/things/{thing_id}/uptime", headers, params=params
        )
        return UptimeResponse.model_validate(resp.json())

    async def get_channels(
        self,
        thing_id: str,
        headers: dict,
        *,
        limit: int = 10,
        offset: int = 0,
        connected: bool | None = None,
    ) -> ChannelsPage:
        params: dict = {"limit": limit, "offset": offset}
        if connected is not None:
            params["connected"] = connected
        resp = await self.client.request(
            "GET", f"/iot/things/{thing_id}/channels", headers, params=params
        )
        return ChannelsPage.model_validate(resp.json())
