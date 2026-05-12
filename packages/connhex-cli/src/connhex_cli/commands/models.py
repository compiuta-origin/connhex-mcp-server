import asyncio

import typer

from connhex_cli.context import CLIContext
from connhex_cli.dependencies import get_models_service
from connhex_cli.output import render

models_app = typer.Typer(help="Manage device models.")


@models_app.command("list")
def list_models(
    ctx: typer.Context,
    limit: int = typer.Option(10, help="Max items."),
    offset: int = typer.Option(0, help="Items to skip."),
    name: str | None = typer.Option(None, help="Filter by name."),
    order: str | None = typer.Option(None, help="Sort field: id or name."),
    dir: str | None = typer.Option(None, help="Sort direction: asc or desc."),
    tag: str | None = typer.Option(None, help="Filter by tag."),
    tenant: str | None = typer.Option(None, help="Filter by tenant."),
) -> None:
    """List device models."""
    cli_ctx: CLIContext = ctx.obj
    svc = get_models_service(ctx)

    async def _run():
        return await svc.list(
            {},
            limit=limit,
            offset=offset,
            name=name,
            order=order,
            dir=dir,
            tag=tag,
            tenant=tenant,
        )

    result = asyncio.run(_run())
    render(result.models, cli_ctx.output)


@models_app.command("get")
def get_model(ctx: typer.Context, model_id: str = typer.Argument(...)) -> None:
    """Get a device model by ID."""
    cli_ctx: CLIContext = ctx.obj
    svc = get_models_service(ctx)

    async def _run():
        return await svc.get(model_id, {})

    render(asyncio.run(_run()), cli_ctx.output)


@models_app.command("things")
def model_things(
    ctx: typer.Context,
    model_id: str = typer.Argument(...),
    limit: int = typer.Option(10, help="Max items."),
    offset: int = typer.Option(0, help="Items to skip."),
    order: str | None = typer.Option(None, help="Sort field."),
    dir: str | None = typer.Option(None, help="Sort direction."),
) -> None:
    """List things assigned to a model."""
    cli_ctx: CLIContext = ctx.obj
    svc = get_models_service(ctx)

    async def _run():
        return await svc.get_things(
            model_id, {}, limit=limit, offset=offset, order=order, dir=dir
        )

    result = asyncio.run(_run())
    render(result.things, cli_ctx.output)
