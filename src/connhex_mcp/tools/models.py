from typing import Annotated, Literal

from fastmcp.server.dependencies import get_http_headers

from connhex_mcp.dependencies import get_models_service
from connhex_mcp.mcp_instance import mcp
from connhex_mcp.services.models import Model, ModelsPage
from connhex_mcp.services.things import ThingsPage


@mcp.tool()
async def get_model(
    model_id: Annotated[str, "UUID of the model."],
) -> Model:
    """Get a single device model by ID."""
    headers = get_http_headers() or {}
    data = await get_models_service().get(model_id, headers)
    return Model.model_validate(data)


@mcp.tool()
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
    headers = get_http_headers() or {}
    data = await get_models_service().list(
        headers,
        limit=limit,
        offset=offset,
        name=name,
        order=order,
        dir=dir,
        tag=tag,
        tenant=tenant,
    )
    return ModelsPage.model_validate(data)


@mcp.tool()
async def get_model_things(
    model_id: Annotated[str, "UUID of the model."],
    limit: Annotated[int, "Max items to return."] = 10,
    offset: Annotated[int, "Number of items to skip."] = 0,
    order: Annotated[Literal["id", "name"] | None, "Sort field."] = None,
    dir: Annotated[Literal["asc", "desc"] | None, "Sort direction."] = None,
) -> ThingsPage:
    """List all things assigned to a specific device model."""
    headers = get_http_headers() or {}
    data = await get_models_service().get_things(
        model_id, headers, limit=limit, offset=offset, order=order, dir=dir
    )
    return ThingsPage.model_validate(data)
