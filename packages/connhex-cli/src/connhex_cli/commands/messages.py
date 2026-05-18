import typer
from connhex.errors import ConnhexAPIError
from connhex.schemas.reader import DecimationFunc, DecimationType, ReadFormat

from connhex_cli.client import connhex_client
from connhex_cli.context import CLIContext
from connhex_cli.output import render

messages_app = typer.Typer(help="Read messages from channels and things.")


@messages_app.command("channel")
def channel_messages(
    ctx: typer.Context,
    channel_id: str = typer.Argument(...),
    limit: int = typer.Option(100, help="Max messages."),
    offset: int = typer.Option(0),
    from_s: float | None = typer.Option(
        None, "--from", help="Start Unix epoch seconds."
    ),
    to_s: float | None = typer.Option(
        None, "--to", help="End Unix epoch seconds."
    ),
    format: ReadFormat = typer.Option("messages"),
    name: str | None = typer.Option(None, help="SenML name filter."),
    publisher: str | None = typer.Option(None, help="Publisher UUID filter."),
    ds: str | None = typer.Option(
        None, help='Decimation granularity, e.g. "5m".'
    ),
    dsf: DecimationFunc | None = typer.Option(
        None, help="Decimation function."
    ),
    dsv: DecimationType | None = typer.Option(None, help="Decimation type."),
) -> None:
    """Read messages from a channel."""
    cli_ctx: CLIContext = ctx.obj
    c = connhex_client(ctx)
    result = c.reader.read_messages(
        channel_id=channel_id,
        limit=limit,
        offset=offset,
        from_s=from_s,
        to_s=to_s,
        publisher=publisher,
        name=name,
        format=format,
        ds=ds,
        dsf=dsf,
        dsv=dsv,
    )
    render(result, cli_ctx.output)


@messages_app.command("thing")
def thing_messages(
    ctx: typer.Context,
    thing_id: str = typer.Argument(...),
    limit: int = typer.Option(100, help="Max messages."),
    offset: int = typer.Option(0),
    from_s: float | None = typer.Option(
        None, "--from", help="Start Unix epoch seconds."
    ),
    to_s: float | None = typer.Option(
        None, "--to", help="End Unix epoch seconds."
    ),
    format: ReadFormat = typer.Option("messages"),
    name: str | None = typer.Option(None, help="SenML name filter."),
    publisher: str | None = typer.Option(None, help="Publisher UUID filter."),
    ds: str | None = typer.Option(
        None, help='Decimation granularity, e.g. "5m".'
    ),
    dsf: DecimationFunc | None = typer.Option(
        None, help="Decimation function."
    ),
    dsv: DecimationType | None = typer.Option(None, help="Decimation type."),
) -> None:
    """Read messages for a thing (resolves channel automatically)."""
    cli_ctx: CLIContext = ctx.obj
    c = connhex_client(ctx)

    thing = c.things.get(thing_id)
    metadata = thing.metadata
    if isinstance(metadata, dict):
        channel_id = metadata.get("event_channel_id")
    elif metadata is not None:
        channel_id = metadata.event_channel_id
    else:
        channel_id = None

    if not channel_id:
        raise ConnhexAPIError(
            status=404,
            detail=f"Thing {thing_id} has no 'event_channel_id' in metadata.",
        )

    result = c.reader.read_messages(
        channel_id=channel_id,
        limit=limit,
        offset=offset,
        from_s=from_s,
        to_s=to_s,
        publisher=publisher,
        name=name,
        format=format,
        ds=ds,
        dsf=dsf,
        dsv=dsv,
    )
    render(result, cli_ctx.output)
