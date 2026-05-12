from functools import lru_cache

from connhex_sdk.auth.resolver import AuthResolver
from connhex_sdk.client import ConnhexClient
from connhex_sdk.iam import IAMService
from connhex_sdk.models import ModelsService
from connhex_sdk.reader import ReaderService
from connhex_sdk.resources import ResourcesService
from connhex_sdk.rules_engine import RulesEngineService
from connhex_sdk.things import ThingsService
from fastmcp.server.dependencies import get_access_token

from connhex_mcp.config import MCPSettings


def _fastmcp_validated_token() -> str | None:
    """Return the fastmcp-validated OAuth access token, if any."""
    try:
        access_token = get_access_token()
    except Exception:
        return None
    if access_token and access_token.token:
        return access_token.token
    return None


@lru_cache(maxsize=1)
def get_settings() -> MCPSettings:
    return MCPSettings()  # type: ignore[call-arg]


@lru_cache(maxsize=1)
def get_auth_resolver() -> AuthResolver:
    settings = get_settings()
    return AuthResolver(
        settings,
        validated_token_getter=_fastmcp_validated_token,
        prefer_validated_token=settings.public_url is not None,
    )


@lru_cache(maxsize=1)
def get_connhex_client() -> ConnhexClient:
    return ConnhexClient(get_settings(), get_auth_resolver())


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
