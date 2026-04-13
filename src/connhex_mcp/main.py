import argparse
import importlib
import pkgutil

import connhex_mcp.resources
import connhex_mcp.tools
from connhex_mcp.mcp_instance import mcp

# Auto-discover and register all tools and resources
for _pkg in (connhex_mcp.tools, connhex_mcp.resources):
    for _, _module_name, _ in pkgutil.iter_modules(_pkg.__path__):
        importlib.import_module(f"{_pkg.__name__}.{_module_name}")

TRANSPORTS = ["stdio", "http", "sse", "streamable-http"]


def main():
    parser = argparse.ArgumentParser(description="Connhex MCP Server")
    parser.add_argument(
        "--transport",
        choices=TRANSPORTS,
        default="stdio",
        help="Transport protocol",
    )
    args = parser.parse_args()

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
