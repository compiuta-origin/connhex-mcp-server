from typing import Annotated, Literal

from connhex.models import Model, ModelsPage
from connhex.things import ThingsPage
from mcp.types import ToolAnnotations

from connhex_mcp.client import get_connhex
from connhex_mcp.mcp_instance import mcp


@mcp.tool(
    title="Get Thing Model",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def get_model(
    model_id: Annotated[str, "UUID of the model."],
) -> Model:
    """Get a single device model by ID."""
    return await get_connhex().models.get(model_id)


@mcp.tool(
    title="List Thing Models",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def list_models(
    limit: Annotated[int, "Max items to return (1–100)."] = 10,
    offset: Annotated[int, "Number of items to skip."] = 0,
    name: Annotated[
        str | None, "Filter by name (case-insensitive partial match)."
    ] = None,
    order: Annotated[Literal["id", "name"] | None, "Sort field."] = None,
    dir: Annotated[Literal["asc", "desc"] | None, "Sort direction."] = None,
    tag: Annotated[str | None, "Filter by tag."] = None,
    tenant: Annotated[str | None, "Filter by tenant."] = None,
) -> ModelsPage:
    """List device models with optional filtering and pagination."""
    return await get_connhex().models.list(
        limit=limit,
        offset=offset,
        name=name,
        order=order,
        dir=dir,
        tag=tag,
        tenant=tenant,
    )


@mcp.tool(
    title="List Model Things",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def get_model_things(
    model_id: Annotated[str, "UUID of the model."],
    limit: Annotated[int, "Max items to return."] = 10,
    offset: Annotated[int, "Number of items to skip."] = 0,
    order: Annotated[Literal["id", "name"] | None, "Sort field."] = None,
    dir: Annotated[Literal["asc", "desc"] | None, "Sort direction."] = None,
) -> ThingsPage:
    """List all things assigned to a specific device model."""
    return await get_connhex().models.get_things(
        model_id, limit=limit, offset=offset, order=order, dir=dir
    )
