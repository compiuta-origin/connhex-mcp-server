import json

from connhex_mcp.client import get_connhex
from connhex_mcp.mcp_instance import mcp

SCHEMA_DESCRIPTION = """
Schema of every resource type exposed by this Connhex JSON:API service for
the current deployment.

Shape:
- Top-level keys are resource type names. Use them as the `resource_type`
  argument to the corresponding *_resource tools.
- Each value is a dict of fields:
    - Entries with a `type` key are attributes (e.g. `String`, `Date`,
      `Object`). `isArray: true` indicates a list-valued attribute.
    - Entries with a `link` key are relationships. The `link` value is the
      related resource type — pass it (or a comma-separated list) as the
      `include` argument to fetch related records inline. `isArray: true`
      means a to-many relationship; `inverse` is the field name on the other
      side.

Internal/system fields present on every type:
- `tenants`, `createdAt`, `updatedAt` are managed by the platform. Do NOT
  include them in create/update payloads and do not surface them as
  user-facing data unless explicitly asked.

Read this resource before constructing filters, includes, or create/update
payloads — it is the source of truth for valid types and field names.
"""


@mcp.resource(
    uri="connhex://resources/schema",
    name="Connhex Resources schema",
    mime_type="application/json",
    description=SCHEMA_DESCRIPTION,
)
async def resources_schema() -> str:
    data = await get_connhex().resources.get_schema()
    return json.dumps(data)


@mcp.resource(
    uri="connhex://manufacturing/schema",
    name="Connhex Manufacturing schema",
    mime_type="application/json",
    description=SCHEMA_DESCRIPTION,
)
async def manufacturing_schema() -> str:
    data = await get_connhex().manufacturing.get_schema()
    return json.dumps(data)
