from contextlib import asynccontextmanager

from fastmcp import FastMCP

from connhex_mcp import __version__
from connhex_mcp.client import get_connhex


@asynccontextmanager
async def lifespan(_server):
    try:
        yield
    finally:
        # Only close if a client was actually built; avoid forcing creation
        # during shutdown of a server that never served a request.
        if get_connhex.cache_info().currsize:
            await get_connhex().close()


mcp = FastMCP(
    "connhex",
    version=__version__,
    instructions=(
        "Connhex MCP server. Use these tools to interact with a Connhex Cloud instance."
    ),
    lifespan=lifespan,
)
