from typing import Callable

from fastmcp.server.dependencies import get_http_headers
from mcp.types import ToolAnnotations

from connhex_mcp.dependencies import (
    get_manufacturing_service,
    get_resources_service,
)
from connhex_mcp.mcp_instance import mcp
from connhex_mcp.resources.schemas import SCHEMA_DESCRIPTION
from connhex_mcp.services.resources import (
    ListResponse,
    Resource,
    ResourcesService,
)
from connhex_mcp.utils.jsonapi import flatten_response

_SCHEMA_HINT = (
    "\nCall the `get_schema` tool first to discover valid resource types, "
    "attributes, and relationships.\n"
)

LIST_DOC = f"""
List resources of a given type from a Connhex JSON:API service.

Args:
    resource_type: The resource type name (e.g., "devices", "plants").
    filter: JSON:API filter tree. The dict is walked recursively and
        translated into `filter[...][...]=value` query params. Examples:
            {{"serial": "ABC"}}                          → exact match (default)
            {{"serial": ["A", "B"]}}                     → match any of A or B
            {{"serial": {{"fuzzy-match": "ABC"}}}}         → case-insensitive prefix
            {{"createdAt": {{"min": "2024-01-01",
                           "max": "2024-12-31"}}}}        → range
            {{"site": {{"exists": True}}}}                → presence check
            {{"address.city": "Milan"}}                  → object property (dot)
            {{"site:name": {{"fuzzy-match": "Plant"}}}}    → related-resource property (colon)
            {{"or": {{"name": {{"fuzzy-match": "x"}},
                    "serial": {{"fuzzy-match": "x"}}}}}}   → OR across fields
        Operators: match (default, can be omitted), fuzzy-match, min, max, exists.
        Combinators: and (default), or — top-level only, cannot be mixed.
        Field names come from the schema resource (see below).
    sort: Comma-separated fields. Prefix with "-" for descending.
    include: Comma-separated related resources to include inline. When set,
        the response's relationship references are replaced with the full
        nested resources from `included`.
    fields: Sparse fieldsets, mapping resource type → comma-separated field
        names (e.g. {{"devices": "serial,name"}}). Use this aggressively to
        keep responses small.
    page_limit: Number of results per page (default 25).
    page_offset: Offset for pagination.
{_SCHEMA_HINT}"""

GET_DOC = f"""
Get a specific resource by its ID from a Connhex JSON:API service.

Args:
    resource_type: The resource type name.
    resource_id: The resource's unique ID.
    include: Comma-separated related resources to include inline.
{_SCHEMA_HINT}"""

CREATE_DOC = f"""
Create a new resource on a Connhex JSON:API service.

Args:
    resource_type: The resource type name.
    attributes: Dict of attribute values for the new resource.
    relationships: Optional dict of JSON:API relationships.
{_SCHEMA_HINT}"""

UPDATE_DOC = f"""
Update an existing resource's attributes (partial update).

Args:
    resource_type: The resource type name.
    resource_id: The resource's unique ID.
    attributes: Dict of attribute values to update.
{_SCHEMA_HINT}"""

DELETE_DOC = f"""
Delete a resource. This action is irreversible.

Args:
    resource_type: The resource type name.
    resource_id: The resource's unique ID.
{_SCHEMA_HINT}"""


async def _list_resources(
    service: ResourcesService,
    resource_type: str,
    filter: dict | None = None,
    sort: str | None = None,
    include: str | None = None,
    fields: dict | None = None,
    page_limit: int = 25,
    page_offset: int = 0,
) -> dict:
    headers = get_http_headers() or {}
    result = await service.list(
        resource_type=resource_type,
        headers=headers,
        filter=filter,
        sort=sort,
        include=include,
        fields=fields,
        page_limit=page_limit,
        page_offset=page_offset,
    )
    return flatten_response(result)


async def _get_resource(
    service: ResourcesService,
    resource_type: str,
    resource_id: str,
    include: str | None = None,
) -> dict:
    headers = get_http_headers() or {}
    result = await service.get(
        resource_type=resource_type,
        ids=resource_id,
        headers=headers,
        include=include,
    )
    return flatten_response(result)


async def _create_resource(
    service: ResourcesService,
    resource_type: str,
    attributes: dict,
    relationships: dict | None = None,
) -> dict:
    headers = get_http_headers() or {}
    payload = {
        "data": {
            "type": resource_type,
            "attributes": attributes,
        }
    }
    if relationships:
        payload["data"]["relationships"] = relationships

    result = await service.create(resource_type, payload, headers)
    return flatten_response(result)


async def _update_resource(
    service: ResourcesService,
    resource_type: str,
    resource_id: str,
    attributes: dict,
) -> dict:
    headers = get_http_headers() or {}
    payload = {
        "data": {
            "type": resource_type,
            "id": resource_id,
            "attributes": attributes,
        }
    }
    result = await service.update(resource_type, resource_id, payload, headers)
    return flatten_response(result)


async def _delete_resource(
    service: ResourcesService,
    resource_type: str,
    resource_id: str,
) -> str:
    headers = get_http_headers() or {}
    await service.delete(resource_type, resource_id, headers)
    return f"Resource {resource_id} of type '{resource_type}' deleted successfully."


def _register_jsonapi_tools(
    service_getter: Callable[[], ResourcesService],
    name_for: Callable[[str], str],
    title_prefix: str,
) -> None:
    async def list_op(
        resource_type: str,
        filter: dict | None = None,
        sort: str | None = None,
        include: str | None = None,
        fields: dict | None = None,
        page_limit: int = 25,
        page_offset: int = 0,
    ) -> ListResponse[Resource]:
        result = await _list_resources(
            service=service_getter(),
            resource_type=resource_type,
            filter=filter,
            sort=sort,
            include=include,
            fields=fields,
            page_limit=page_limit,
            page_offset=page_offset,
        )
        return ListResponse[Resource].model_validate(result)

    async def get_op(
        resource_type: str,
        resource_id: str,
        include: str | None = None,
    ) -> Resource:
        result = await _get_resource(
            service=service_getter(),
            resource_type=resource_type,
            resource_id=resource_id,
            include=include,
        )
        return Resource.model_validate(result["data"])

    async def create_op(
        resource_type: str,
        attributes: dict,
        relationships: dict | None = None,
    ) -> Resource:
        result = await _create_resource(
            service=service_getter(),
            resource_type=resource_type,
            attributes=attributes,
            relationships=relationships,
        )
        return Resource.model_validate(result["data"])

    async def update_op(
        resource_type: str,
        resource_id: str,
        attributes: dict,
    ) -> Resource:
        result = await _update_resource(
            service=service_getter(),
            resource_type=resource_type,
            resource_id=resource_id,
            attributes=attributes,
        )
        return Resource.model_validate(result["data"])

    async def delete_op(
        resource_type: str,
        resource_id: str,
    ) -> str:
        return await _delete_resource(
            service=service_getter(),
            resource_type=resource_type,
            resource_id=resource_id,
        )

    mcp.tool(
        name=name_for("list"),
        description=LIST_DOC,
        title=f"List {title_prefix}s",
        annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
    )(list_op)
    mcp.tool(
        name=name_for("get"),
        description=GET_DOC,
        title=f"Get {title_prefix}",
        annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
    )(get_op)
    mcp.tool(
        name=name_for("create"),
        description=CREATE_DOC,
        title=f"Create {title_prefix}",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, openWorldHint=False
        ),
    )(create_op)
    mcp.tool(
        name=name_for("update"),
        description=UPDATE_DOC,
        title=f"Update {title_prefix}",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, openWorldHint=False
        ),
    )(update_op)
    mcp.tool(
        name=name_for("delete"),
        description=DELETE_DOC,
        title=f"Delete {title_prefix}",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, openWorldHint=False
        ),
    )(delete_op)


@mcp.tool(
    title="Get Service Schema",
    description=SCHEMA_DESCRIPTION,
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def get_schema() -> dict:
    headers = get_http_headers() or {}
    return {
        "resources": await get_resources_service().get_schema(headers),
        "manufacturing": await get_manufacturing_service().get_schema(headers),
    }


_RESOURCES_NAMES = {
    "list": "list_resources",
    "get": "get_resource",
    "create": "create_resource",
    "update": "update_resource",
    "delete": "delete_resource",
}

_MANUFACTURING_NAMES = {
    "list": "list_manufacturing_resources",
    "get": "get_manufacturing_resource",
    "create": "create_manufacturing_resource",
    "update": "update_manufacturing_resource",
    "delete": "delete_manufacturing_resource",
}

_register_jsonapi_tools(
    get_resources_service, _RESOURCES_NAMES.__getitem__, "Resource"
)
_register_jsonapi_tools(
    get_manufacturing_service,
    _MANUFACTURING_NAMES.__getitem__,
    "Manufacturing Resource",
)
