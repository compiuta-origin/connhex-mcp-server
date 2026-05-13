import asyncio

import typer
from pydantic import ValidationError

from connhex_cli.commands.connectables.register import run
from connhex_cli.context import CLIContext
from connhex_cli.dependencies import (
    get_manufacturing_service,
    get_provision_service,
)
from connhex_cli.output import render

connectables_app = typer.Typer(help="Manage connectables.")


@connectables_app.command("register")
def register_connectables(
    ctx: typer.Context,
    file: str = typer.Argument(
        ..., help="Path to a CSV/JSON file, or '-' to read from stdin."
    ),
    format: str | None = typer.Option(
        None,
        "--format",
        case_sensitive=False,
        help="Input format: csv | json. Required when reading from stdin.",
    ),
    schema: str = typer.Option(
        "device", "--schema", help="Manufacturing resource type."
    ),
    serial_number_field: str = typer.Option(
        "serial_number",
        "--serial-number-field",
        help="Manufacturing field to fill with provision.init_id.",
    ),
    connhex_id_field: str = typer.Option(
        "connhex_id",
        "--connhex-id-field",
        help="Manufacturing field to fill with the provisioned thing ID.",
    ),
) -> None:
    """Bulk-register connectables from a CSV/JSON file (or stdin).

    For each row this performs two operations atomically:

      1. Bulk-provision the device via the provision API.
      2. Create a record in the manufacturing service for the
         configured --schema, auto-filling --serial-number-field
         with provision.init_id and --connhex-id-field with the
         provisioned thing's ID.

    If step 2 fails for any row the provisioned things from step 1
    are rolled back.

    INPUT FORMAT
    Both CSV and JSON use the same flat dotted-key layout:

      provision.init_id       (required) external identifier
      provision.init_key      external key (auto-generated UUID if omitted)
      provision.name
      provision.model         UUID of the device model
      provision.migration_key
      provision.migration_key_quota
      manufacturing.<field>   any attribute in the --schema's manifest
      tenant                  optional tenant id

    JSON may also use the nested shape
    {"provision": {...}, "manufacturing": {...}, "tenant": "..."}.

    EXAMPLES
      connhex-cli connectables register ./connectables.csv
      connhex-cli connectables register ./connectables.json --schema sensors
      cat connectables.json | connhex-cli connectables register - --format json
    """
    cli_ctx: CLIContext = ctx.obj

    try:
        result = asyncio.run(
            run(
                file,
                format.lower() if format else None,
                schema=schema,
                serial_field=serial_number_field,
                connhex_field=connhex_id_field,
                provision_svc=get_provision_service(ctx),
                manufacturing_svc=get_manufacturing_service(ctx),
            )
        )
    except ValidationError as e:
        typer.echo(f"Validation failed:\n{e}", err=True)
        raise typer.Exit(1)

    render(result, cli_ctx.output)


__all__ = ["connectables_app"]
