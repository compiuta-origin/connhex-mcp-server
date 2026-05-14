"""Singleton AsyncConnhex client wired from MCP settings.

Tools and resources import `get_connhex()` and call services directly:
`await get_connhex().things.get(thing_id)`. The client is built lazily on
first use and closed via the FastMCP `lifespan` context manager registered
on the server instance.
"""

from functools import lru_cache

from connhex import AsyncConnhex

from connhex_mcp.auth.token_resolver import build_token_provider
from connhex_mcp.config import MCPSettings


@lru_cache(maxsize=1)
def get_settings() -> MCPSettings:
    return MCPSettings()  # type: ignore[call-arg]


@lru_cache(maxsize=1)
def get_connhex() -> AsyncConnhex:
    settings = get_settings()
    return AsyncConnhex(
        instance_url=str(settings.instance_url),
        token_provider=build_token_provider(settings),
    )
