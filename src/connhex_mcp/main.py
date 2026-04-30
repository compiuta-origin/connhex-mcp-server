import argparse
import importlib
import pkgutil

import connhex_mcp.resources
import connhex_mcp.tools
from connhex_mcp.auth.remote import ConnhexOAuthProvider
from connhex_mcp.dependencies import get_settings
from connhex_mcp.logging_setup import setup_logging
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
    parser.add_argument(
        "--mode",
        choices=["local", "remote"],
        default="local",
        help=("Server mode: local (stdio) or remote (streamable-http + OAuth)"),
    )
    args = parser.parse_args()

    settings = get_settings()
    log_config = setup_logging(settings.log_config_path)

    if settings.disabled_tools:
        mcp.disable(names=set(settings.disabled_tools), components={"tool"})

    if args.mode == "remote":
        assert settings.public_url, (
            "CONNHEX_PUBLIC_URL must be set when running in remote mode"
        )

        mcp.auth = ConnhexOAuthProvider(settings)
        mcp.run(
            transport="streamable-http",
            host="0.0.0.0",
            path="/",
            uvicorn_config={"log_config": log_config},
        )
    else:
        http_transports = {"http", "sse", "streamable-http"}
        if args.transport in http_transports:
            mcp.run(
                transport=args.transport,
                uvicorn_config={"log_config": log_config},
            )
        else:
            mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
