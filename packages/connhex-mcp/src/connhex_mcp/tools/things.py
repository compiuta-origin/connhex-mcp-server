from typing import Annotated, Literal

from connhex_sdk.things import (
    BatchStatusRes,
    ChannelsPage,
    FlappingResponse,
    StatusSummary,
    Thing,
    ThingsPage,
    UptimeResponse,
)
from fastmcp.server.dependencies import get_http_headers
from mcp.types import ToolAnnotations

from connhex_mcp.dependencies import get_things_service
from connhex_mcp.mcp_instance import mcp


@mcp.tool(
    title="Get Thing",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def get_thing(
    thing_id: Annotated[str, "UUID of the thing to retrieve."],
) -> Thing:
    """Get a single thing by ID."""
    headers = get_http_headers() or {}
    return await get_things_service().get(thing_id, headers)


@mcp.tool(
    title="List Things",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def list_things(
    limit: Annotated[int, "Max items to return (1–100)."] = 50,
    offset: Annotated[int, "Number of items to skip."] = 0,
    name: Annotated[
        str | None, "Filter by name (case-insensitive partial match)."
    ] = None,
    order: Annotated[Literal["id", "name"] | None, "Sort field."] = None,
    dir: Annotated[Literal["asc", "desc"] | None, "Sort direction."] = None,
) -> ThingsPage:
    """List things with optional filtering and pagination."""
    headers = get_http_headers() or {}
    return await get_things_service().list(
        headers,
        limit=limit,
        offset=offset,
        name=name,
        order=order,
        dir=dir,
    )


@mcp.tool(
    title="Get Things Connectivity Status",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def get_things_status(
    ids: Annotated[list[str], "Thing UUIDs to fetch connectivity status for."],
) -> BatchStatusRes:
    """Get current connectivity status for a batch of things by their IDs.
    Things that have never connected are omitted from the response."""
    headers = get_http_headers() or {}
    return await get_things_service().get_status(ids, headers)


@mcp.tool(
    title="Get Fleet Connectivity Summary",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def get_things_status_summary() -> StatusSummary:
    """Get a fleet-wide connectivity summary: online, offline, never connected, active last hour."""
    headers = get_http_headers() or {}
    return await get_things_service().get_status_summary(headers)


@mcp.tool(
    title="Get Flapping Things",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def get_things_flapping(
    window: Annotated[
        str | None, 'Observation window, e.g. "1h". Defaults to "1h" upstream.'
    ] = None,
    min_reconnects: Annotated[
        int | None,
        "Minimum reconnect count to include. Defaults to 10 upstream.",
    ] = None,
    limit: Annotated[
        int | None, "Max results. Defaults to 100 upstream."
    ] = None,
) -> FlappingResponse:
    """List devices with an excessive number of reconnections (flapping) within a time window."""
    headers = get_http_headers() or {}
    return await get_things_service().get_flapping(
        headers,
        window=window,
        min_reconnects=min_reconnects,
        limit=limit,
    )


@mcp.tool(
    title="Get Thing Uptime",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def get_thing_uptime(
    thing_id: Annotated[str, "UUID of the thing."],
    from_ts: Annotated[
        int, "Start of range as Unix timestamp (seconds). Max range is 90 days."
    ],
    to_ts: Annotated[int, "End of range as Unix timestamp (seconds)."],
) -> UptimeResponse:
    """Get the connect/disconnect timeline and total uptime for a single thing within a time range."""
    headers = get_http_headers() or {}
    return await get_things_service().get_uptime(
        thing_id, headers, from_ts=from_ts, to_ts=to_ts
    )


@mcp.tool(
    title="List Thing Channels",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def get_thing_channels(
    thing_id: Annotated[str, "UUID of the thing."],
    limit: Annotated[int, "Max items to return."] = 10,
    offset: Annotated[int, "Number of items to skip."] = 0,
    connected: Annotated[bool | None, "Filter by connection state."] = None,
) -> ChannelsPage:
    """List the channels connected to a specific thing."""
    headers = get_http_headers() or {}
    return await get_things_service().get_channels(
        thing_id, headers, limit=limit, offset=offset, connected=connected
    )
