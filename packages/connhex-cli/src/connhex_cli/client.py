import typer
from connhex import Connhex
from connhex.urls import DEFAULT_INSTANCE_URL

from connhex_cli.auth import provider
from connhex_cli.context import CLIContext


def connhex_client(ctx: typer.Context) -> Connhex:
    cli_ctx: CLIContext = ctx.obj
    token = provider.get_token(cli_ctx.token)
    instance_url = (
        provider.get_instance_url(cli_ctx.instance_url) or DEFAULT_INSTANCE_URL
    )
    client = Connhex(instance_url=instance_url, token=token)
    ctx.call_on_close(client.close)
    return client
