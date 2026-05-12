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
    return await get_iam_service().whoami()
