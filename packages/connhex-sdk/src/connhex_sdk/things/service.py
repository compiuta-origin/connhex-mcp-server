# Required: the `list` method below shadows the builtin, and `list[str]`
# annotations on later methods would resolve to it without this import.
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

    async def get(self, thing_id: str) -> Thing:
        resp = await self.client.request("GET", f"/iot/things/{thing_id}")
        return Thing.model_validate(resp.json())

    async def list(
        self,
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
        resp = await self.client.request("GET", "/iot/things", params=params)
        return ThingsPage.model_validate(resp.json())

    async def get_status(self, ids: list[str]) -> BatchStatusRes:
        resp = await self.client.request(
            "POST",
            "/iot/things/status",
            json={"ids": ids},
            extra_headers={"Content-Type": "application/json"},
        )
        return BatchStatusRes.model_validate(resp.json())

    async def get_status_summary(self) -> StatusSummary:
        resp = await self.client.request("GET", "/iot/things/status/summary")
        return StatusSummary.model_validate(resp.json())

    async def get_flapping(
        self,
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
            "GET", "/iot/things/status/flapping", params=params
        )
        return FlappingResponse.model_validate(resp.json())

    async def get_uptime(
        self,
        thing_id: str,
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
            "GET", f"/iot/things/{thing_id}/uptime", params=params
        )
        return UptimeResponse.model_validate(resp.json())

    async def get_channels(
        self,
        thing_id: str,
        *,
        limit: int = 10,
        offset: int = 0,
        connected: bool | None = None,
    ) -> ChannelsPage:
        params: dict = {"limit": limit, "offset": offset}
        if connected is not None:
            params["connected"] = connected
        resp = await self.client.request(
            "GET", f"/iot/things/{thing_id}/channels", params=params
        )
        return ChannelsPage.model_validate(resp.json())
