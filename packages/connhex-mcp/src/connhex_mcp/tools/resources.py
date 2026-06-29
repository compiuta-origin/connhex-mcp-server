from typing import Annotated, Callable

from connhex.aio.services.resources import ResourcesService
from connhex.schemas.resources import ListResponse, Resource
from mcp.types import ToolAnnotations

from connhex_mcp.client import get_connhex
from connhex_mcp.mcp_instance import mcp
from connhex_mcp.resources.schemas import SCHEMA_DESCRIPTION

_SCHEMA_HINT = (
    "\nIf available, call the `get_schema` tool first to discover valid "
    "resource types, attributes, and relationships.\n"
)

FILTER_DESCRIPTION = """
JSON:API filter tree. The dict is walked recursively and translated into
`filter[...][...]=value` query params. Examples:
    {"serial": "ABC"}                          → exact match (default)
    {"serial": ["A", "B"]}                     → match any of A or B
    {"serial": {"fuzzy-match": "ABC"}}         → case-insensitive prefix
    {"createdAt": {"min": "2024-01-01",
                   "max": "2024-12-31"}}        → range
    {"site": {"exists": True}}                 → presence check
    {"address.city": "Milan"}                  → object property (dot)
    {"site:name": {"fuzzy-match": "Plant"}}    → related-resource property (colon)
    {"or": {"name": {"fuzzy-match": "x"},
            "serial": {"fuzzy-match": "x"}}}   → OR across fields

NOTE: do not filter a relationship directly by its resource ID (for example,
{"installation": "<installation-id>"} is not supported). Relationship filters
must end in an actual attribute from the related resource, such as
{"installation:name": "Plant A"}. When only a related resource ID is known,
first call `get_resource` for it, extract a suitable attribute, then call
`list_resources` with a `relationship:attribute` filter. For example: get the
installation by ID, read its `name`, then list devices with
{"installation:name": "<installation-name>"}.

A relation path is one literal, flat dict key: use {"installation:name": "Plant A"},
never nest it as {"installation": {"name": "Plant A"}}.
To verify that a match belongs to a specific related resource ID,
set `include` to the relationship name (for example, `include="installation"`)
and compare its returned ID.

Operators: match (default, can be omitted), fuzzy-match, min, max, exists.
Combinators: and (default), or — top-level only, cannot be mixed.
Field names come from the schema resource.
"""

ResourceType = Annotated[
    str,
    'Resource type name from get_schema, e.g. "devices" or "plants".',
]
ResourceId = Annotated[str, "Resource ID."]
Filter = Annotated[dict | None, FILTER_DESCRIPTION]
Sort = Annotated[
    str | None,
    'Comma-separated sort fields. Prefix a field with "-" for descending.',
]
Include = Annotated[
    str | None,
    "Comma-separated relationship names to include inline. Use this whenever "
    "the answer needs data from related resources: it replaces relationship "
    "references with full nested included resources and avoids a second API "
    'call.\nExample: to find devices for an installation, call resource_type="devices", '
    'filter={"installation:name": "Plant A"}, include="installation" so each '
    "device result includes the matched installation details.",
]
PageLimit = Annotated[int, "Number of results per page."]
PageOffset = Annotated[int, "Pagination offset."]
Attributes = Annotated[
    dict,
    "Resource attributes payload. Field names must come from get_schema.",
]
Relationships = Annotated[
    dict | None,
    "Optional JSON:API relationships payload.",
]

LIST_DOC = f"""
List resources of a given type from a JSON:API service.

Supports filtering, sorting, relationship includes, and
pagination. Argument details are provided in the parameter schema.
{_SCHEMA_HINT}"""

GET_DOC = f"""
Get a specific resource by its ID from a JSON:API service.

Use `include` when related resources should be returned inline.
{_SCHEMA_HINT}"""

CREATE_DOC = f"""
Create a new resource on a Connhex JSON:API service.

Use schema fields for attributes and relationships.
{_SCHEMA_HINT}"""

UPDATE_DOC = f"""
Update an existing resource's attributes (partial update).

Use schema fields for attributes. Only provided attributes are changed.
{_SCHEMA_HINT}"""

DELETE_DOC = f"""
Delete a resource. This action is irreversible.
{_SCHEMA_HINT}"""


async def _list_resources(
    service: ResourcesService,
    resource_type: ResourceType,
    filter: Filter = None,
    sort: Sort = None,
    include: Include = None,
    page_limit: PageLimit = 25,
    page_offset: PageOffset = 0,
) -> ListResponse[Resource]:
    return await service.list(
        resource_type=resource_type,
        filter=filter,
        sort=sort,
        include=include,
        page_limit=page_limit,
        page_offset=page_offset,
    )


async def _get_resource(
    service: ResourcesService,
    resource_type: ResourceType,
    resource_id: ResourceId,
    include: Include = None,
) -> Resource:
    return await service.get(
        resource_type=resource_type,
        ids=resource_id,
        include=include,
    )


async def _create_resource(
    service: ResourcesService,
    resource_type: ResourceType,
    attributes: Attributes,
    relationships: Relationships = None,
) -> Resource:
    payload = {
        "data": {
            "type": resource_type,
            "attributes": attributes,
        }
    }
    if relationships:
        payload["data"]["relationships"] = relationships

    return await service.create(resource_type, payload)


async def _update_resource(
    service: ResourcesService,
    resource_type: ResourceType,
    resource_id: ResourceId,
    attributes: Attributes,
) -> Resource:
    payload = {
        "data": {
            "type": resource_type,
            "id": resource_id,
            "attributes": attributes,
        }
    }
    return await service.update(resource_type, resource_id, payload)


async def _delete_resource(
    service: ResourcesService,
    resource_type: ResourceType,
    resource_id: ResourceId,
) -> str:
    await service.delete(resource_type, resource_id)
    return f"Resource {resource_id} of type '{resource_type}' deleted successfully."


def _register_jsonapi_tools(
    service_getter: Callable[[], ResourcesService],
    name_for: Callable[[str], str],
    title_prefix: str,
) -> None:
    async def list_op(
        resource_type: ResourceType,
        filter: Filter = None,
        sort: Sort = None,
        include: Include = None,
        page_limit: PageLimit = 25,
        page_offset: PageOffset = 0,
    ) -> ListResponse[Resource]:
        return await _list_resources(
            service=service_getter(),
            resource_type=resource_type,
            filter=filter,
            sort=sort,
            include=include,
            page_limit=page_limit,
            page_offset=page_offset,
        )

    async def get_op(
        resource_type: ResourceType,
        resource_id: ResourceId,
        include: Include = None,
    ) -> Resource:
        return await _get_resource(
            service=service_getter(),
            resource_type=resource_type,
            resource_id=resource_id,
            include=include,
        )

    async def create_op(
        resource_type: ResourceType,
        attributes: Attributes,
        relationships: Relationships = None,
    ) -> Resource:
        return await _create_resource(
            service=service_getter(),
            resource_type=resource_type,
            attributes=attributes,
            relationships=relationships,
        )

    async def update_op(
        resource_type: ResourceType,
        resource_id: ResourceId,
        attributes: Attributes,
    ) -> Resource:
        return await _update_resource(
            service=service_getter(),
            resource_type=resource_type,
            resource_id=resource_id,
            attributes=attributes,
        )

    async def delete_op(
        resource_type: ResourceType,
        resource_id: ResourceId,
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
        annotations=ToolAnnotations(
            readOnlyHint=True, destructiveHint=False, openWorldHint=False
        ),
    )(list_op)
    mcp.tool(
        name=name_for("get"),
        description=GET_DOC,
        title=f"Get {title_prefix}",
        annotations=ToolAnnotations(
            readOnlyHint=True, destructiveHint=False, openWorldHint=False
        ),
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
    annotations=ToolAnnotations(
        readOnlyHint=True, destructiveHint=False, openWorldHint=False
    ),
)
async def get_schema() -> dict:
    connhex = get_connhex()
    return {
        "resources": await connhex.resources.get_schema(),
        "manufacturing": await connhex.manufacturing.get_schema(),
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
    lambda: get_connhex().resources,
    _RESOURCES_NAMES.__getitem__,
    "Resource",
)
_register_jsonapi_tools(
    lambda: get_connhex().manufacturing,
    _MANUFACTURING_NAMES.__getitem__,
    "Manufacturing Resource",
)
