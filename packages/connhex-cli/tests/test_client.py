import click
from connhex.urls import DEFAULT_INSTANCE_URL

from connhex_cli.client import connhex_client
from connhex_cli.context import CLIContext


def test_token_mode_uses_default_instance_url_without_stored_creds():
    ctx = click.Context(
        click.Command("test"),
        obj=CLIContext(instance_url=None, token="token", output="json"),
    )

    client = connhex_client(ctx)

    try:
        assert client._http.instance_url == DEFAULT_INSTANCE_URL
        assert client._http._token == "token"
    finally:
        ctx.close()
