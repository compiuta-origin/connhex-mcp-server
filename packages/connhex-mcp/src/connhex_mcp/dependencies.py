from functools import lru_cache

from connhex_sdk.client import ConnhexClient
from connhex_sdk.iam import IAMService
from connhex_sdk.models import ModelsService
from connhex_sdk.reader import ReaderService
from connhex_sdk.resources import ResourcesService
from connhex_sdk.rules_engine import RulesEngineService
from connhex_sdk.things import ThingsService

from connhex_mcp.auth.token_resolver import build_token_provider
from connhex_mcp.config import MCPSettings


@lru_cache(maxsize=1)
def get_settings() -> MCPSettings:
    return MCPSettings()  # type: ignore[call-arg]


@lru_cache(maxsize=1)
def get_connhex_client() -> ConnhexClient:
    settings = get_settings()
    return ConnhexClient(
        instance_url=str(settings.instance_url),
        token_provider=build_token_provider(settings),
    )


@lru_cache(maxsize=1)
def get_iam_service() -> IAMService:
    return IAMService(get_connhex_client())


@lru_cache(maxsize=1)
def get_resources_service() -> ResourcesService:
    return ResourcesService(get_connhex_client(), "resources")


@lru_cache(maxsize=1)
def get_manufacturing_service() -> ResourcesService:
    return ResourcesService(get_connhex_client(), "manufacturing")


@lru_cache(maxsize=1)
def get_things_service() -> ThingsService:
    return ThingsService(get_connhex_client())


@lru_cache(maxsize=1)
def get_reader_service() -> ReaderService:
    return ReaderService(get_connhex_client())


@lru_cache(maxsize=1)
def get_models_service() -> ModelsService:
    return ModelsService(get_connhex_client())


@lru_cache(maxsize=1)
def get_rules_engine_service() -> RulesEngineService:
    return RulesEngineService(get_connhex_client())
