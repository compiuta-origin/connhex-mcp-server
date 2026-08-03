from typing import Annotated

from connhex.errors import ConnhexAPIError
from connhex.schemas.reader import (
    DecimationFunc,
    DecimationType,
    MessagesPage,
    ReadFormat,
)
from mcp.types import ToolAnnotations

from connhex_mcp.client import get_connhex
from connhex_mcp.mcp_instance import mcp

Limit = Annotated[int, "Max messages to return (upstream max is 1500)."]
Offset = Annotated[int, "Pagination offset."]
FromS = Annotated[
    float,
    "Required start time in Unix epoch seconds. Always provide a bounded range "
    "together with to_s; narrow time ranges prevent slow database queries and "
    "timeouts. The integer part represents whole seconds; "
    "the fractional part provides sub-second precision (e.g. 1744243200.183767).",
]
ToS = Annotated[
    float,
    "Required end time in Unix epoch seconds. Always provide a bounded range "
    "together with from_s; narrow time ranges prevent slow database queries and "
    "timeouts. The integer part represents whole seconds; "
    "the fractional part provides sub-second precision (e.g. 1744243200.183767).",
]
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
    from_s: float | None,
    to_s: float | None,
    publisher: str | None,
    name: str | None,
    format: ReadFormat,
    ds: str | None,
    dsf: DecimationFunc | None,
    dsv: DecimationType | None,
) -> MessagesPage:
    return await get_connhex().reader.read_messages(
        channel_id=channel_id,
        limit=limit,
        offset=offset,
        from_s=from_s,
        to_s=to_s,
        publisher=publisher,
        name=name,
        format=format,
        ds=ds,
        dsf=dsf,
        dsv=dsv,
    )


@mcp.tool(
    title="Read Channel Messages",
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, openWorldHint=False
    ),
)
async def read_channel_messages(
    channel_id: Annotated[str, "UUID of the channel."],
    from_s: FromS,
    to_s: ToS,
    limit: Limit = 10,
    offset: Offset = 0,
    publisher: Publisher = None,
    name: Name = None,
    format: Format = "messages",
    ds: Ds = None,
    dsf: Dsf = None,
    dsv: Dsv = None,
) -> MessagesPage:
    """Read messages from a Connhex IoT channel by its channel ID.

    Use this when you already have a channel ID. To go from a device's
    business identifier (serial, etc.) to messages, prefer
    `read_thing_messages`, which resolves the channel ID for you from a
    thing ID.
    """
    return await _read_channel_messages(
        channel_id=channel_id,
        limit=limit,
        offset=offset,
        from_s=from_s,
        to_s=to_s,
        publisher=publisher,
        name=name,
        format=format,
        ds=ds,
        dsf=dsf,
        dsv=dsv,
    )


@mcp.tool(
    title="Read Thing Messages",
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, openWorldHint=False
    ),
)
async def read_thing_messages(
    thing_id: Annotated[
        str,
        "Thing ID (UUID). "
        "This is the value of the Connhex ID field on the resource "
        "or manufacturing record — not the resource's own id.",
    ],
    from_s: FromS,
    to_s: ToS,
    limit: Limit = 10,
    offset: Offset = 0,
    publisher: Publisher = None,
    name: Name = None,
    format: Format = "messages",
    ds: Ds = None,
    dsf: Dsf = None,
    dsv: Dsv = None,
) -> MessagesPage:
    """Read messages for a Connhex thing (device/edge), identified by its
    thing ID. Resolves the thing's `event_channel_id` from its metadata and
    reads messages from it.

    Resolving a user-facing identifier:
        If you only have a serial number or another business identifier,
        first use list_resources / list_manufacturing_resources to find the record,
        then look for a field named connhexId (or similar) —
        that value is the thing_id to pass here, not the record's own id.
    """
    thing = await get_connhex().things.get(thing_id)

    metadata = thing.metadata
    if isinstance(metadata, dict):
        channel_id = metadata.get("event_channel_id")
        meta_keys = sorted(metadata.keys()) if not channel_id else []
    elif metadata is not None:
        channel_id = metadata.event_channel_id
        meta_keys = (
            sorted(metadata.model_dump().keys()) if not channel_id else []
        )
    else:
        channel_id = None
        meta_keys = []
    if not channel_id:
        raise ConnhexAPIError(
            status=404,
            detail=(
                f"Thing {thing_id} has no 'event_channel_id' in its metadata. "
                f"Available metadata keys: {meta_keys}"
            ),
        )

    return await _read_channel_messages(
        channel_id=channel_id,
        limit=limit,
        offset=offset,
        from_s=from_s,
        to_s=to_s,
        publisher=publisher,
        name=name,
        format=format,
        ds=ds,
        dsf=dsf,
        dsv=dsv,
    )
