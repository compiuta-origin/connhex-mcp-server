from fastmcp.server.dependencies import get_http_headers
from mcp.types import ToolAnnotations

from connhex_mcp.dependencies import get_iam_service
from connhex_mcp.mcp_instance import mcp


@mcp.tool(
    title="Get Current User and Session",
    annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False),
)
async def whoami() -> dict:
    """
    Returns information about the currently authenticated user.
    Use this to verify the connection and see user's identity (active Ory Kratos session).
    """
    headers = get_http_headers() or {}
    iam_service = get_iam_service()
    return await iam_service.whoami(headers)
