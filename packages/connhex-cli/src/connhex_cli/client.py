"""Build and run an `AsyncConnhex` for a single CLI command.

Commands call `run(ctx, fn)` where `fn` is an async callable taking the
client. The helper wraps `asyncio.run` and an `async with` so the
underlying httpx pool is properly closed at command exit.
"""

import asyncio
from typing import Awaitable, Callable, TypeVar

import typer
from connhex import AsyncConnhex

from connhex_cli.auth import provider
from connhex_cli.context import CLIContext

T = TypeVar("T")


def _make_connhex(ctx: typer.Context) -> AsyncConnhex:
    cli_ctx: CLIContext = ctx.obj
    token = provider.get_token(cli_ctx.token)
    instance_url = provider.get_instance_url(cli_ctx.instance_url)
    if not instance_url:
        typer.echo(
            "No instance URL. Run `connhex login` or set --instance-url.",
            err=True,
        )
        raise typer.Exit(1)
    return AsyncConnhex(instance_url=instance_url, token=token)


def run(ctx: typer.Context, fn: Callable[[AsyncConnhex], Awaitable[T]]) -> T:
    async def _inner() -> T:
        async with _make_connhex(ctx) as c:
            return await fn(c)

    return asyncio.run(_inner())
