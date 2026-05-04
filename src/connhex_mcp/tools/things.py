from typing import Annotated, Literal

from fastmcp.server.dependencies import get_http_headers

from connhex_mcp.dependencies import get_things_service
from connhex_mcp.mcp_instance import mcp
from connhex_mcp.services.things import (
    BatchStatusRes,
    ChannelsPage,
    FlappingResponse,
    StatusSummary,
    Thing,
    ThingsPage,
    UptimeResponse,
)


@mcp.tool()
async def get_thing(
    thing_id: Annotated[str, "UUID of the thing to retrieve."],
) -> Thing:
    """Get a single thing by ID."""
    headers = get_http_headers() or {}
    data = await get_things_service().get(thing_id, headers)
    return Thing.model_validate(data)


@mcp.tool()
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
    data = await get_things_service().list(
        headers,
        limit=limit,
        offset=offset,
        name=name,
        order=order,
        dir=dir,
    )
    return ThingsPage.model_validate(data)


@mcp.tool()
async def get_things_status(
    ids: Annotated[list[str], "Thing UUIDs to fetch connectivity status for."],
) -> BatchStatusRes:
    """Get current connectivity status for a batch of things by their IDs.
    Things that have never connected are omitted from the response."""
    headers = get_http_headers() or {}
    data = await get_things_service().get_status(ids, headers)
    return BatchStatusRes.model_validate(data)


@mcp.tool()
async def get_things_status_summary() -> StatusSummary:
    """Get a fleet-wide connectivity summary: online, offline, never connected, active last hour."""
    headers = get_http_headers() or {}
    data = await get_things_service().get_status_summary(headers)
    return StatusSummary.model_validate(data)


@mcp.tool()
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
    data = await get_things_service().get_flapping(
        headers,
        window=window,
        min_reconnects=min_reconnects,
        limit=limit,
    )
    return FlappingResponse.model_validate(data)


@mcp.tool()
async def get_thing_uptime(
    thing_id: Annotated[str, "UUID of the thing."],
    from_ts: Annotated[
        int, "Start of range as Unix timestamp (seconds). Max range is 90 days."
    ],
    to_ts: Annotated[int, "End of range as Unix timestamp (seconds)."],
) -> UptimeResponse:
    """Get the connect/disconnect timeline and total uptime for a single thing within a time range."""
    headers = get_http_headers() or {}
    data = await get_things_service().get_uptime(
        thing_id, headers, from_ts=from_ts, to_ts=to_ts
    )
    return UptimeResponse.model_validate(data)


@mcp.tool()
async def get_thing_channels(
    thing_id: Annotated[str, "UUID of the thing."],
    limit: Annotated[int, "Max items to return."] = 10,
    offset: Annotated[int, "Number of items to skip."] = 0,
    connected: Annotated[bool | None, "Filter by connection state."] = None,
) -> ChannelsPage:
    """List the channels connected to a specific thing."""
    headers = get_http_headers() or {}
    data = await get_things_service().get_channels(
        thing_id, headers, limit=limit, offset=offset, connected=connected
    )
    return ChannelsPage.model_validate(data)
