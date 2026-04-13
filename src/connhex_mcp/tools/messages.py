from typing import Annotated

from fastmcp.server.dependencies import get_http_headers

from connhex_mcp.dependencies import get_reader_service, get_things_service
from connhex_mcp.mcp_instance import mcp
from connhex_mcp.services.reader import (
    DecimationFunc,
    DecimationType,
    ReadFormat,
)
from connhex_mcp.utils.errors import ConnhexAPIError

Limit = Annotated[int, "Max messages to return (upstream max is 1500)."]
Offset = Annotated[int, "Pagination offset."]
FromNs = Annotated[int | None, "Start time in nanoseconds (Unix epoch)."]
ToNs = Annotated[int | None, "End time in nanoseconds (Unix epoch)."]
Publisher = Annotated[str | None, "Publisher UUID filter."]
Name = Annotated[
    str | None,
    "SenML name (metric URN) filter. Only applies to SenML-based formats"
    ' ("messages", "params", "metrics"). Ignored for "infos".',
]
Format = Annotated[
    ReadFormat,
    "Which Connhex Message Policy (CMP) component to read. "
    '"messages" (default): time-series sensor data collected during '
    "operation (e.g. temperature, pressure). SenML format. Most common "
    "format — use for actual measurements or telemetry. "
    '"params": runtime-editable configuration parameters of the device '
    "(e.g. operating mode, thresholds). SenML format. Use to inspect or "
    "verify device settings. "
    '"infos": static or rarely-changing device metadata sent at boot or '
    "after firmware updates (e.g. serial number, firmware version, "
    "hardware revision). JSON format (not SenML). Use to identify or "
    "describe the device. name, ds, dsf, and dsv do not apply to this "
    "format. "
    '"metrics": internal device performance indicators (e.g. CPU usage, '
    "RAM consumption, uptime). SenML format. Use for device health "
    "monitoring and diagnostics.",
]
Ds = Annotated[
    str | None,
    'Decimation granularity, format "<number><s|m|h|d|w|M|y>" '
    '(e.g. "5m", "1h", "1d"). When set, the upstream service buckets '
    "messages and aggregates them with dsf. Only applies to SenML-based "
    'formats ("messages", "params", "metrics").',
]
Dsf = Annotated[
    DecimationFunc | None,
    "Aggregation function for decimation: max, min, avg, sum, stddev, "
    'variance. Defaults to "avg" upstream.',
]
Dsv = Annotated[
    DecimationType | None,
    'Decimation value type: "v" for numeric SenML values, "vb" for '
    'boolean. Defaults to "v" upstream.',
]


async def _read_channel_messages(
    channel_id: str,
    limit: int,
    offset: int,
    from_ns: int | None,
    to_ns: int | None,
    publisher: str | None,
    name: str | None,
    format: ReadFormat,
    ds: str | None,
    dsf: DecimationFunc | None,
    dsv: DecimationType | None,
) -> dict:
    headers = get_http_headers() or {}
    return await get_reader_service().read_messages(
        channel_id=channel_id,
        headers=headers,
        limit=limit,
        offset=offset,
        from_ns=from_ns,
        to_ns=to_ns,
        publisher=publisher,
        name=name,
        format=format,
        ds=ds,
        dsf=dsf,
        dsv=dsv,
    )


@mcp.tool()
async def read_channel_messages(
    channel_id: Annotated[str, "UUID of the channel."],
    limit: Limit = 100,
    offset: Offset = 0,
    from_ns: FromNs = None,
    to_ns: ToNs = None,
    publisher: Publisher = None,
    name: Name = None,
    format: Format = "messages",
    ds: Ds = None,
    dsf: Dsf = None,
    dsv: Dsv = None,
) -> dict:
    """Read messages from a Connhex IoT channel by its channel ID.

    Use this when you already have a channel ID. To go from a device's
    business identifier (serial, etc.) to messages, prefer
    `read_thing_messages`, which resolves the channel ID for you from a
    Connhex thing ID.
    """
    return await _read_channel_messages(
        channel_id=channel_id,
        limit=limit,
        offset=offset,
        from_ns=from_ns,
        to_ns=to_ns,
        publisher=publisher,
        name=name,
        format=format,
        ds=ds,
        dsf=dsf,
        dsv=dsv,
    )


@mcp.tool()
async def read_thing_messages(
    thing_id: Annotated[
        str, "Connhex thing UUID (the IoT thing/device/edge ID)."
    ],
    limit: Limit = 100,
    offset: Offset = 0,
    from_ns: FromNs = None,
    to_ns: ToNs = None,
    publisher: Publisher = None,
    name: Name = None,
    format: Format = "messages",
    ds: Ds = None,
    dsf: Dsf = None,
    dsv: Dsv = None,
) -> dict:
    """Read messages for a Connhex IoT thing (device/edge), identified by
    its Connhex thing ID. Resolves the thing's `event_channel_id` from its
    metadata and reads messages from it.

    Resolving a user-facing identifier:
        If you only have a serial number or another business identifier,
        first use the `list_resources` / `list_manufacturing_resources`
        tools to find a record matching that identifier and read the field
        that links to the IoT thing (commonly `connhexId`, but the exact
        field depends on the deployment). Read the
        `connhex://resources/schema` resource if you are unsure which field
        maps to the thing ID. Then pass that thing ID here.
    """
    headers = get_http_headers() or {}
    thing = await get_things_service().get(thing_id, headers)

    metadata = thing.get("metadata") or {}
    channel_key = "event_channel_id"
    channel_id = metadata.get(channel_key)
    if not channel_id:
        raise ConnhexAPIError(
            status=404,
            detail=(
                f"Thing {thing_id} has no '{channel_key}' in its metadata. "
                f"Available metadata keys: {sorted(metadata.keys())}"
            ),
        )

    return await _read_channel_messages(
        channel_id=channel_id,
        limit=limit,
        offset=offset,
        from_ns=from_ns,
        to_ns=to_ns,
        publisher=publisher,
        name=name,
        format=format,
        ds=ds,
        dsf=dsf,
        dsv=dsv,
    )
