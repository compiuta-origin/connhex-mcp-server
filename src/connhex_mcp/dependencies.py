from functools import lru_cache

from connhex_mcp.auth.resolver import AuthResolver
from connhex_mcp.client import ConnhexClient
from connhex_mcp.config import Settings
from connhex_mcp.services.iam import IAMService
from connhex_mcp.services.reader import ReaderService
from connhex_mcp.services.resources import ResourcesService
from connhex_mcp.services.things import ThingsService


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore


@lru_cache(maxsize=1)
def get_auth_resolver() -> AuthResolver:
    return AuthResolver(get_settings())


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
