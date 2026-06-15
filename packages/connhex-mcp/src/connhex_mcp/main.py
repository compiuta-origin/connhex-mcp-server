import argparse
import importlib
import logging
import pkgutil

import uvicorn
from fastmcp import FastMCP
from fastmcp.server.server import Transport
from fastmcp.server.transforms import ToolTransform
from fastmcp.tools.tool_transform import ToolTransformConfig
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

import connhex_mcp.resources
import connhex_mcp.tools
from connhex_mcp import __version__
from connhex_mcp.auth.remote import ConnhexOAuthProvider
from connhex_mcp.config import MCPSettings
from connhex_mcp.client import get_settings
from connhex_mcp.logging_setup import setup_logging
from connhex_mcp.mcp_instance import mcp
from connhex_mcp.middleware import OriginValidationMiddleware

logger = logging.getLogger(__name__)

# Auto-discover and register all tools and resources
for _pkg in (connhex_mcp.tools, connhex_mcp.resources):
    for _, _module_name, _ in pkgutil.iter_modules(_pkg.__path__):
        importlib.import_module(f"{_pkg.__name__}.{_module_name}")

TRANSPORTS = ["stdio", "http", "sse", "streamable-http"]


def _apply_tool_transforms(server: FastMCP, settings: MCPSettings) -> None:
    if not settings.tool_transforms:
        return

    server.add_transform(
        ToolTransform(
            {
                name: ToolTransformConfig(
                    description=override.description,
                    title=override.title,
                )
                for name, override in settings.tool_transforms.items()
            }
        )
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Connhex MCP Server")
    parser.add_argument(
        "--version",
        action="version",
        version=f"connhex-mcp {__version__}",
    )
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
        help="Server mode: local (stdio) or remote (streamable-http + OAuth)",
    )
    return parser.parse_args()


def _run_remote(settings: MCPSettings, log_config: dict) -> None:
    assert settings.public_url, (
        "CONNHEX_PUBLIC_URL must be set when running in remote mode"
    )
    mcp.auth = ConnhexOAuthProvider(settings)
    http_app = mcp.http_app(
        transport="streamable-http",
        path="/",
        middleware=[
            Middleware(
                OriginValidationMiddleware, allowed_origin=settings.public_url
            ),
            Middleware(
                CORSMiddleware,
                allow_origins=[settings.public_url],
                allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
                allow_headers=[
                    "mcp-protocol-version",
                    "mcp-session-id",
                    "Authorization",
                    "Content-Type",
                ],
                expose_headers=["mcp-session-id"],
            ),
        ],
    )
    uvicorn.run(http_app, host="0.0.0.0", log_config=log_config)


def _run_local(transport: Transport, log_config: dict) -> None:
    http_transports = {"http", "sse", "streamable-http"}
    if transport in http_transports:
        mcp.run(transport=transport, uvicorn_config={"log_config": log_config})
    else:
        mcp.run(transport=transport)


def main():
    args = _parse_args()
    settings = get_settings()
    log_config = setup_logging(settings.log_config_path)

    logger.info("connhex-mcp %s starting (mode=%s)", __version__, args.mode)

    _apply_tool_transforms(mcp, settings)

    if settings.disabled_tools:
        mcp.disable(names=set(settings.disabled_tools), components={"tool"})

    if args.mode == "remote":
        _run_remote(settings, log_config)
    else:
        _run_local(args.transport, log_config)


if __name__ == "__main__":
    main()
