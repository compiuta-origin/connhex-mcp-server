"""Orchestrate the `connectables register` flow.

Steps:
1. Load rows from CSV/JSON/stdin.
2. Fetch manufacturing schema (cached on the SDK service).
3. Validate the batch via Pydantic.
4. Bulk-provision via ProvisionService.
5. Per device, create a manufacturing record (JSON:API).
6. On any manufacturing failure, roll back the bulk provision.
"""

import typer
from connhex.errors import ConnhexAPIError
from connhex.provision import ProvisionService
from connhex.resources import ResourcesService

from connhex_cli.commands.connectables.casing import snake_to_camel
from connhex_cli.commands.connectables.loader import load
from connhex_cli.commands.connectables.schemas import (
    Connectable,
    ConnectablesBatch,
)


def _extract_schema_attrs(schema_doc: dict, resource_type: str) -> set[str]:
    """Pull field names for `resource_type` from a manufacturing schema doc."""
    if not isinstance(schema_doc, dict) or not schema_doc:
        raise typer.BadParameter(
            "manufacturing schema response is empty or malformed"
        )
    type_def = schema_doc.get(resource_type)
    if not isinstance(type_def, dict):
        available = ", ".join(sorted(schema_doc.keys()))
        raise typer.BadParameter(
            f"schema '{resource_type}' not found in manufacturing schema. "
            f"Available: {available}. Pass --schema <name>."
        )
    return set(type_def.keys())


def _manufacturing_payload(
    c: Connectable,
    thing_id: str,
    *,
    resource_type: str,
    serial_field: str,
    connhex_field: str,
) -> dict:
    attributes = {
        **c.manufacturing,
        serial_field: c.provision.init_id,
        connhex_field: thing_id,
    }
    if c.tenant:
        # "tenants" is always an available schema field (optional)
        attributes["tenants"] = [c.tenant] if c.tenant else None
    return {
        "data": {
            "type": resource_type,
            "attributes": attributes,
        }
    }


async def run(
    source: str,
    fmt: str | None,
    *,
    schema: str,
    serial_field: str,
    connhex_field: str,
    provision_svc: ProvisionService,
    manufacturing_svc: ResourcesService,
) -> dict:
    rows = load(source, fmt)
    if not rows:
        raise typer.BadParameter("no rows found in input")

    # Schema attributes are always camelCase; normalize the CLI defaults
    # (which use snake_case for ergonomics) before any comparison.
    serial_field = snake_to_camel(serial_field)
    connhex_field = snake_to_camel(connhex_field)

    schema_doc = await manufacturing_svc.get_schema()
    schema_attrs = _extract_schema_attrs(schema_doc, schema)

    batch = ConnectablesBatch.model_validate(
        {"items": rows},
        context={
            "schema_attrs": schema_attrs,
            "serial_field": serial_field,
            "connhex_field": connhex_field,
        },
    )

    bulk = await provision_svc.bulk_provision(
        [c.provision for c in batch.items]
    )

    if bulk.failed:
        raise typer.BadParameter(
            f"bulk provision failed: processed={bulk.processed} "
            f"failed={bulk.failed} errors={bulk.errors}"
        )
    if len(bulk.things) != len(batch.items):
        raise typer.BadParameter(
            f"provisioned {len(bulk.things)} things but submitted "
            f"{len(batch.items)} items; aborting"
        )

    created = []
    try:
        for connectable, thing in zip(batch.items, bulk.things):
            payload = _manufacturing_payload(
                connectable,
                thing.id,
                resource_type=schema,
                serial_field=serial_field,
                connhex_field=connhex_field,
            )
            await manufacturing_svc.create(schema, payload)
            created.append(thing.id)
    except ConnhexAPIError as e:
        await provision_svc.bulk_unprovision([t.id for t in bulk.things])
        raise typer.BadParameter(
            f"manufacturing create failed after {len(created)}/"
            f"{len(bulk.things)} records; rolled back all provisioned "
            f"things. Error: {e}"
        ) from e

    return {
        "registered": len(bulk.things),
        "things": [
            {"id": t.id, "name": t.name, "key": t.key} for t in bulk.things
        ],
    }
