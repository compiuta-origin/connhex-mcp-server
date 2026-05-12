import typer
from connhex_sdk.auth.resolver import AuthResolver
from connhex_sdk.client import ConnhexClient
from connhex_sdk.config import AuthType, CoreSettings
from connhex_sdk.iam import IAMService
from connhex_sdk.models import ModelsService
from connhex_sdk.reader import ReaderService
from connhex_sdk.resources import ResourcesService
from connhex_sdk.rules_engine import RulesEngineService
from connhex_sdk.things import ThingsService

from connhex_cli.auth import provider
from connhex_cli.context import CLIContext


def _make_client(ctx: typer.Context) -> ConnhexClient:
    cli_ctx: CLIContext = ctx.obj
    token = provider.get_token(cli_ctx.token)
    instance_url = provider.get_instance_url(cli_ctx.instance_url)
    if not instance_url:
        typer.echo(
            "No instance URL. Run `connhex login` or set --instance-url.",
            err=True,
        )
        raise typer.Exit(1)

    settings = CoreSettings(
        instance_url=instance_url,
        auth_type=AuthType.TOKEN,
        bearer_token=token,
    )
    resolver = AuthResolver(settings)
    return ConnhexClient(settings, resolver)


def get_things_service(ctx: typer.Context) -> ThingsService:
    return ThingsService(_make_client(ctx))


def get_models_service(ctx: typer.Context) -> ModelsService:
    return ModelsService(_make_client(ctx))


def get_reader_service(ctx: typer.Context) -> ReaderService:
    return ReaderService(_make_client(ctx))


def get_resources_service(ctx: typer.Context) -> ResourcesService:
    return ResourcesService(_make_client(ctx), "resources")


def get_manufacturing_service(ctx: typer.Context) -> ResourcesService:
    return ResourcesService(_make_client(ctx), "manufacturing")


def get_rules_service(ctx: typer.Context) -> RulesEngineService:
    return RulesEngineService(_make_client(ctx))


def get_iam_service(ctx: typer.Context) -> IAMService:
    return IAMService(_make_client(ctx))
