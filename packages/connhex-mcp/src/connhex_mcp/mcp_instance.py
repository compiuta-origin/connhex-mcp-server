from fastmcp import FastMCP

from connhex_mcp import __version__

mcp = FastMCP(
    "connhex",
    version=__version__,
    instructions=(
        "Connhex MCP server. Use these tools to interact with a Connhex Cloud instance."
    ),
)
