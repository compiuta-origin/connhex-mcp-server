import asyncio

import typer

from connhex_cli.context import CLIContext
from connhex_cli.dependencies import get_things_service
from connhex_cli.output import render

things_app = typer.Typer(help="Manage things (devices).")


@things_app.command("list")
def list_things(
    ctx: typer.Context,
    limit: int = typer.Option(50, help="Max items to return."),
    offset: int = typer.Option(0, help="Items to skip."),
    name: str | None = typer.Option(None, help="Filter by name."),
    order: str | None = typer.Option(None, help="Sort field: id or name."),
    dir: str | None = typer.Option(None, help="Sort direction: asc or desc."),
) -> None:
    """List things with optional filtering."""
    cli_ctx: CLIContext = ctx.obj
    svc = get_things_service(ctx)

    async def _run():
        return await svc.list(
            {}, limit=limit, offset=offset, name=name, order=order, dir=dir
        )

    result = asyncio.run(_run())
    render(result.things, cli_ctx.output)


@things_app.command("get")
def get_thing(ctx: typer.Context, thing_id: str = typer.Argument(...)) -> None:
    """Get a single thing by ID."""
    cli_ctx: CLIContext = ctx.obj
    svc = get_things_service(ctx)

    async def _run():
        return await svc.get(thing_id, {})

    render(asyncio.run(_run()), cli_ctx.output)


@things_app.command("status")
def get_status(
    ctx: typer.Context,
    ids: list[str] = typer.Argument(..., help="Thing IDs to check."),
) -> None:
    """Get connectivity status for one or more things."""
    cli_ctx: CLIContext = ctx.obj
    svc = get_things_service(ctx)

    async def _run():
        return await svc.get_status(ids, {})

    render(asyncio.run(_run()), cli_ctx.output)


@things_app.command("status-summary")
def status_summary(ctx: typer.Context) -> None:
    """Get fleet-wide connectivity summary."""
    cli_ctx: CLIContext = ctx.obj
    svc = get_things_service(ctx)

    async def _run():
        return await svc.get_status_summary({})

    render(asyncio.run(_run()), cli_ctx.output)


@things_app.command("flapping")
def flapping(
    ctx: typer.Context,
    window: str | None = typer.Option(
        None, help='Observation window, e.g. "1h".'
    ),
    min_reconnects: int | None = typer.Option(
        None, help="Minimum reconnect count."
    ),
    limit: int | None = typer.Option(None, help="Max results."),
) -> None:
    """List devices with excessive reconnections."""
    cli_ctx: CLIContext = ctx.obj
    svc = get_things_service(ctx)

    async def _run():
        return await svc.get_flapping(
            {}, window=window, min_reconnects=min_reconnects, limit=limit
        )

    render(asyncio.run(_run()), cli_ctx.output)


@things_app.command("uptime")
def uptime(
    ctx: typer.Context,
    thing_id: str = typer.Argument(...),
    from_ts: int = typer.Option(..., "--from", help="Start Unix timestamp."),
    to_ts: int = typer.Option(..., "--to", help="End Unix timestamp."),
) -> None:
    """Get uptime for a thing within a time range."""
    cli_ctx: CLIContext = ctx.obj
    svc = get_things_service(ctx)

    async def _run():
        return await svc.get_uptime(thing_id, {}, from_ts=from_ts, to_ts=to_ts)

    render(asyncio.run(_run()), cli_ctx.output)


@things_app.command("channels")
def channels(
    ctx: typer.Context,
    thing_id: str = typer.Argument(...),
    limit: int = typer.Option(10, help="Max items."),
    offset: int = typer.Option(0, help="Items to skip."),
    connected: bool | None = typer.Option(
        None, help="Filter by connection state."
    ),
) -> None:
    """List channels connected to a thing."""
    cli_ctx: CLIContext = ctx.obj
    svc = get_things_service(ctx)

    async def _run():
        return await svc.get_channels(
            thing_id, {}, limit=limit, offset=offset, connected=connected
        )

    result = asyncio.run(_run())
    render(result.channels, cli_ctx.output)
