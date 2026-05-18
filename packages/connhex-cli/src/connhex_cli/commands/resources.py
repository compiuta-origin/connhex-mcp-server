import json

import typer

from connhex_cli.client import connhex_client
from connhex_cli.context import CLIContext
from connhex_cli.output import render

resources_app = typer.Typer(help="Manage resources and manufacturing records.")


def _svc(c, manufacturing: bool):
    return c.manufacturing if manufacturing else c.resources


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
    filter: str | None = typer.Option(
        None,
        help=(
            "JSON filter dict. Example: "
            '\'{"name": {"fuzzy-match": "sensor-01"}}\' '
            "(e.g. for resource_type=device)."
        ),
    ),
    fields: str | None = typer.Option(None, help="JSON fields dict."),
) -> None:
    """List resources of a given type."""
    cli_ctx: CLIContext = ctx.obj

    filter_dict = None
    if filter:
        try:
            filter_dict = json.loads(filter)
        except json.JSONDecodeError as e:
            typer.echo(f"Invalid JSON for filter: {e}", err=True)
            raise typer.Exit(1)

    fields_dict = None
    if fields:
        try:
            fields_dict = json.loads(fields)
        except json.JSONDecodeError as e:
            typer.echo(f"Invalid JSON for fields: {e}", err=True)
            raise typer.Exit(1)

    c = connhex_client(ctx)
    result = _svc(c, manufacturing).list(
        resource_type=resource_type,
        page_limit=page_limit,
        page_offset=page_offset,
        sort=sort,
        include=include,
        filter=filter_dict,
        fields=fields_dict,
    )
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
    c = connhex_client(ctx)
    render(
        _svc(c, manufacturing).get(
            resource_type=resource_type,
            ids=resource_id,
            include=include,
        ),
        cli_ctx.output,
    )


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

    c = connhex_client(ctx)
    render(
        _svc(c, manufacturing).create(resource_type, payload),
        cli_ctx.output,
    )


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

    c = connhex_client(ctx)
    render(
        _svc(c, manufacturing).update(resource_type, resource_id, payload),
        cli_ctx.output,
    )


@resources_app.command("delete")
def delete_resource(
    ctx: typer.Context,
    resource_type: str = typer.Argument(...),
    resource_id: str = typer.Argument(...),
    manufacturing: bool = typer.Option(False, "--manufacturing", "-m"),
) -> None:
    """Delete a resource."""
    c = connhex_client(ctx)
    _svc(c, manufacturing).delete(resource_type, resource_id)
    typer.echo(f"Deleted {resource_type}/{resource_id}.")
