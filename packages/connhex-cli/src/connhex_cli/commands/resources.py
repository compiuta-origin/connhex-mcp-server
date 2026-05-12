import asyncio
import json

import typer

from connhex_cli.context import CLIContext
from connhex_cli.dependencies import (
    get_manufacturing_service,
    get_resources_service,
)
from connhex_cli.output import render

resources_app = typer.Typer(help="Manage resources and manufacturing records.")


def _svc(ctx: typer.Context, manufacturing: bool):
    if manufacturing:
        return get_manufacturing_service(ctx)
    return get_resources_service(ctx)


@resources_app.command("list")
def list_resources(
    ctx: typer.Context,
    resource_type: str = typer.Argument(..., help="Resource type name."),
    manufacturing: bool = typer.Option(False, "--manufacturing", "-m"),
    page_limit: int = typer.Option(25, help="Results per page."),
    page_offset: int = typer.Option(0, help="Pagination offset."),
    sort: str | None = typer.Option(None, help="Sort fields."),
    include: str | None = typer.Option(
        None, help="Related resources to include."
    ),
) -> None:
    """List resources of a given type."""
    cli_ctx: CLIContext = ctx.obj
    svc = _svc(ctx, manufacturing)

    async def _run():
        return await svc.list(
            resource_type=resource_type,
            page_limit=page_limit,
            page_offset=page_offset,
            sort=sort,
            include=include,
        )

    result = asyncio.run(_run())
    render(result.data, cli_ctx.output)


@resources_app.command("get")
def get_resource(
    ctx: typer.Context,
    resource_type: str = typer.Argument(...),
    resource_id: str = typer.Argument(...),
    manufacturing: bool = typer.Option(False, "--manufacturing", "-m"),
    include: str | None = typer.Option(None),
) -> None:
    """Get a resource by ID."""
    cli_ctx: CLIContext = ctx.obj
    svc = _svc(ctx, manufacturing)

    async def _run():
        return await svc.get(
            resource_type=resource_type,
            ids=resource_id,
            include=include,
        )

    render(asyncio.run(_run()), cli_ctx.output)


@resources_app.command("create")
def create_resource(
    ctx: typer.Context,
    resource_type: str = typer.Argument(...),
    attributes: str = typer.Argument(..., help="JSON attributes dict."),
    manufacturing: bool = typer.Option(False, "--manufacturing", "-m"),
    relationships: str | None = typer.Option(
        None, help="JSON relationships dict."
    ),
) -> None:
    """Create a new resource."""
    cli_ctx: CLIContext = ctx.obj
    svc = _svc(ctx, manufacturing)

    try:
        attrs = json.loads(attributes)
    except json.JSONDecodeError as e:
        typer.echo(f"Invalid JSON for attributes: {e}", err=True)
        raise typer.Exit(1)

    rels = None
    if relationships:
        try:
            rels = json.loads(relationships)
        except json.JSONDecodeError as e:
            typer.echo(f"Invalid JSON for relationships: {e}", err=True)
            raise typer.Exit(1)

    payload: dict = {"data": {"type": resource_type, "attributes": attrs}}
    if rels:
        payload["data"]["relationships"] = rels

    async def _run():
        return await svc.create(resource_type, payload)

    render(asyncio.run(_run()), cli_ctx.output)


@resources_app.command("update")
def update_resource(
    ctx: typer.Context,
    resource_type: str = typer.Argument(...),
    resource_id: str = typer.Argument(...),
    attributes: str = typer.Argument(..., help="JSON attributes dict."),
    manufacturing: bool = typer.Option(False, "--manufacturing", "-m"),
) -> None:
    """Update a resource's attributes."""
    cli_ctx: CLIContext = ctx.obj
    svc = _svc(ctx, manufacturing)

    try:
        attrs = json.loads(attributes)
    except json.JSONDecodeError as e:
        typer.echo(f"Invalid JSON for attributes: {e}", err=True)
        raise typer.Exit(1)

    payload = {
        "data": {
            "type": resource_type,
            "id": resource_id,
            "attributes": attrs,
        }
    }

    async def _run():
        return await svc.update(resource_type, resource_id, payload)

    render(asyncio.run(_run()), cli_ctx.output)


@resources_app.command("delete")
def delete_resource(
    ctx: typer.Context,
    resource_type: str = typer.Argument(...),
    resource_id: str = typer.Argument(...),
    manufacturing: bool = typer.Option(False, "--manufacturing", "-m"),
) -> None:
    """Delete a resource."""
    svc = _svc(ctx, manufacturing)

    async def _run():
        await svc.delete(resource_type, resource_id)

    asyncio.run(_run())
    typer.echo(f"Deleted {resource_type}/{resource_id}.")
