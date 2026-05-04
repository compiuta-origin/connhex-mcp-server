from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from connhex_mcp.client import ConnhexClient
from connhex_mcp.utils.schemas import ConnhexBaseModel


class ThingMetadata(ConnhexBaseModel):
    cfg_id: str | None = Field(
        default=None, description="Connhex configuration ID of this thing."
    )
    control_channel_id: str | None = Field(
        default=None,
        description="Channel ID used to send commands to the device.",
    )
    event_channel_id: str | None = Field(
        default=None,
        description="Channel ID where the device publishes telemetry.",
    )
    init_id: str | None = Field(
        default=None, description="Hardware initialisation ID (hex string)."
    )
    init_key: str | None = Field(
        default=None, description="Hardware initialisation key (UUID)."
    )
    type: str | None = Field(
        default=None, description='Device type, e.g. "edge".'
    )


class Thing(ConnhexBaseModel):
    id: str = Field(description="Unique thing identifier (UUID).")
    name: str | None = Field(
        default=None, description="Human-readable thing name."
    )
    key: str | None = Field(
        default=None, description="Authentication key (UUID)."
    )
    metadata: ThingMetadata | dict | None = Field(
        default=None,
        description="Device metadata; edge devices include event_channel_id and control_channel_id.",
    )
    model: str | None = Field(
        default=None,
        description="UUID of the device model assigned to this thing.",
    )
    status: ThingStatus | None = Field(
        default=None,
        description="Connectivity status including counters for messages, bytes, and uptime.",
    )


class ThingsPage(ConnhexBaseModel):
    things: list[Thing]
    total: int | None = Field(
        default=None, description="Total number of matching things."
    )
    offset: int | None = Field(
        default=None, description="Number of items skipped."
    )
    limit: int | None = Field(default=None, description="Page size used.")


class ThingStatus(ConnhexBaseModel):
    connected: bool | None = Field(
        default=None, description="Whether the thing is currently connected."
    )
    connected_at: int | None = Field(
        default=None, description="Unix timestamp of the last connection event."
    )
    disconnected_at: int | None = Field(
        default=None,
        description="Unix timestamp of the last disconnection event.",
    )
    last_seen: int | None = Field(
        default=None,
        description="Unix timestamp of the last time the thing was seen.",
    )
    last_message_at: int | None = Field(
        default=None, description="Unix timestamp of the last message received."
    )
    connect_count: int | None = Field(
        default=None, description="Total number of connection events."
    )
    disconnect_count: int | None = Field(
        default=None, description="Total number of disconnection events."
    )
    message_count: int | None = Field(
        default=None, description="Total number of messages received."
    )
    bytes_total: int | None = Field(
        default=None, description="Total bytes transferred."
    )
    total_connected_time: int | None = Field(
        default=None, description="Total connected time in seconds."
    )


class BatchStatusRes(ConnhexBaseModel):
    statuses: dict[str, ThingStatus] = Field(
        description="Connectivity status keyed by thing ID. Things that have never connected are omitted."
    )


class StatusSummary(ConnhexBaseModel):
    online: int | None = Field(
        default=None, description="Number of currently connected devices."
    )
    total: int | None = Field(
        default=None, description="Total number of things."
    )
    never_connected: int | None = Field(
        default=None, description="Things that have never connected."
    )
    active_last_hour: int | None = Field(
        default=None, description="Devices seen in the last hour."
    )
    offline: int | None = Field(
        default=None,
        description="Devices that have connected before but are currently offline.",
    )


class FlappingThing(ConnhexBaseModel):
    thing_id: str = Field(description="Thing identifier.")
    reconnects: int = Field(
        description="Number of connect events within the observation window."
    )


class FlappingResponse(ConnhexBaseModel):
    things: list[FlappingThing] = Field(
        default_factory=list,
        description="Devices ordered by reconnect count descending.",
    )

    @field_validator("things", mode="before")
    @classmethod
    def _none_to_empty(cls, v: object) -> object:
        return v if v is not None else []


class UptimeEvent(ConnhexBaseModel):
    time: int = Field(description="Unix timestamp of the event.")
    event: Literal["connect", "disconnect"] = Field(description="Event type.")


class UptimeResponse(ConnhexBaseModel):
    uptime_seconds: float = Field(
        description="Total connected seconds in the requested time range."
    )
    events: list[UptimeEvent] = Field(
        default_factory=list,
        description="Connect/disconnect events in chronological order.",
    )

    @field_validator("events", mode="before")
    @classmethod
    def _none_to_empty(cls, v: object) -> object:
        return v if v is not None else []


class Channel(ConnhexBaseModel):
    id: str = Field(description="Unique channel identifier (UUID).")
    name: str | None = Field(
        default=None, description="Human-readable channel name."
    )
    metadata: dict | None = Field(
        default=None, description="Arbitrary channel metadata."
    )


class ChannelsPage(ConnhexBaseModel):
    channels: list[Channel]
    total: int | None = Field(
        default=None, description="Total number of matching channels."
    )
    offset: int | None = Field(
        default=None, description="Number of items skipped."
    )
    limit: int | None = Field(default=None, description="Page size used.")


class ThingsService:
    def __init__(self, client: ConnhexClient):
        self.client = client

    async def get(self, thing_id: str, headers: dict) -> dict:
        resp = await self.client.request(
            "GET", f"/iot/things/{thing_id}", headers
        )
        return resp.json()

    async def list(
        self,
        headers: dict,
        *,
        limit: int = 10,
        offset: int = 0,
        name: str | None = None,
        order: str | None = None,
        dir: str | None = None,
    ) -> dict:
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
        return resp.json()

    async def get_status(self, ids: list[str], headers: dict) -> dict:
        resp = await self.client.request(
            "POST",
            "/iot/things/status",
            headers,
            json={"ids": ids},
            extra_headers={"Content-Type": "application/json"},
        )
        return resp.json()

    async def get_status_summary(self, headers: dict) -> dict:
        resp = await self.client.request(
            "GET", "/iot/things/status/summary", headers
        )
        return resp.json()

    async def get_flapping(
        self,
        headers: dict,
        *,
        window: str | None = None,
        min_reconnects: int | None = None,
        limit: int | None = None,
    ) -> dict:
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
        return resp.json()

    async def get_uptime(
        self,
        thing_id: str,
        headers: dict,
        *,
        from_ts: int | None = None,
        to_ts: int | None = None,
    ) -> dict:
        params: dict = {}
        if from_ts is not None:
            params["from"] = from_ts
        if to_ts is not None:
            params["to"] = to_ts
        resp = await self.client.request(
            "GET", f"/iot/things/{thing_id}/uptime", headers, params=params
        )
        return resp.json()

    async def get_channels(
        self,
        thing_id: str,
        headers: dict,
        *,
        limit: int = 10,
        offset: int = 0,
        connected: bool | None = None,
    ) -> dict:
        params: dict = {"limit": limit, "offset": offset}
        if connected is not None:
            params["connected"] = connected
        resp = await self.client.request(
            "GET", f"/iot/things/{thing_id}/channels", headers, params=params
        )
        return resp.json()
