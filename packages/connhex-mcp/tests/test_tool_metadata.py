import pytest

import connhex_mcp.main  # noqa: F401 - registers tools for metadata checks
from connhex_mcp.mcp_instance import mcp


@pytest.mark.asyncio
async def test_all_tools_set_required_annotations():
    tools = await mcp.list_tools()

    missing: list[str] = []
    for tool in tools:
        annotations = tool.annotations
        if annotations is None:
            missing.append(f"{tool.name}: annotations")
            continue
        for field in ("readOnlyHint", "openWorldHint", "destructiveHint"):
            if getattr(annotations, field) is None:
                missing.append(f"{tool.name}: {field}")

    assert missing == []
