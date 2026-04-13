from typing import Callable

from fastmcp.server.dependencies import get_http_headers

from connhex_mcp.dependencies import (
    get_manufacturing_service,
    get_resources_service,
)
from connhex_mcp.mcp_instance import mcp
from connhex_mcp.services.resources import ResourcesService
from connhex_mcp.utils.jsonapi import flatten_response

_SCHEMA_HINT = (
    "\nSchema reference: read the `connhex://resources/schema` resource "
    "(or `connhex://manufacturing/schema` for manufacturing) to discover "
    "valid resource types, attributes, and relationships before calling.\n"
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
) -> None:
    async def list_op(
        resource_type: str,
        filter: dict | None = None,
        sort: str | None = None,
        include: str | None = None,
        fields: dict | None = None,
        page_limit: int = 25,
        page_offset: int = 0,
    ) -> dict:
        return await _list_resources(
            service=service_getter(),
            resource_type=resource_type,
            filter=filter,
            sort=sort,
            include=include,
            fields=fields,
            page_limit=page_limit,
            page_offset=page_offset,
        )

    async def get_op(
        resource_type: str,
        resource_id: str,
        include: str | None = None,
    ) -> dict:
        return await _get_resource(
            service=service_getter(),
            resource_type=resource_type,
            resource_id=resource_id,
            include=include,
        )

    async def create_op(
        resource_type: str,
        attributes: dict,
        relationships: dict | None = None,
    ) -> dict:
        return await _create_resource(
            service=service_getter(),
            resource_type=resource_type,
            attributes=attributes,
            relationships=relationships,
        )

    async def update_op(
        resource_type: str,
        resource_id: str,
        attributes: dict,
    ) -> dict:
        return await _update_resource(
            service=service_getter(),
            resource_type=resource_type,
            resource_id=resource_id,
            attributes=attributes,
        )

    async def delete_op(
        resource_type: str,
        resource_id: str,
    ) -> str:
        return await _delete_resource(
            service=service_getter(),
            resource_type=resource_type,
            resource_id=resource_id,
        )

    mcp.tool(name=name_for("list"), description=LIST_DOC)(list_op)
    mcp.tool(name=name_for("get"), description=GET_DOC)(get_op)
    mcp.tool(name=name_for("create"), description=CREATE_DOC)(create_op)
    mcp.tool(name=name_for("update"), description=UPDATE_DOC)(update_op)
    mcp.tool(name=name_for("delete"), description=DELETE_DOC)(delete_op)


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

_register_jsonapi_tools(get_resources_service, _RESOURCES_NAMES.__getitem__)
_register_jsonapi_tools(
    get_manufacturing_service, _MANUFACTURING_NAMES.__getitem__
)
