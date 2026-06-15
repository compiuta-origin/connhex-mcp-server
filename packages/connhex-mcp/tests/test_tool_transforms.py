import pytest
from fastmcp import FastMCP
from pydantic import ValidationError

from connhex_mcp.config import MCPSettings
from connhex_mcp.main import _apply_tool_transforms


def test_tool_transforms_parse_multiple_tools_from_env(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv(
        "CONNHEX_TOOL_TRANSFORMS",
        """
        {
          "read_thing_messages": {
            "description": "Read deployment-specific thing telemetry.",
            "title": "Read Thing Telemetry"
          },
          "list_things": {
            "description": "List deployment-specific things."
          }
        }
        """,
    )

    settings = MCPSettings()

    assert settings.tool_transforms is not None
    assert (
        settings.tool_transforms["read_thing_messages"].description
        == "Read deployment-specific thing telemetry."
    )
    assert (
        settings.tool_transforms["read_thing_messages"].title
        == "Read Thing Telemetry"
    )
    assert (
        settings.tool_transforms["list_things"].description
        == "List deployment-specific things."
    )
    assert settings.tool_transforms["list_things"].title is None


def test_tool_transforms_reject_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("CONNHEX_TOOL_TRANSFORMS", "{not-json")

    with pytest.raises(ValidationError):
        MCPSettings()


def test_tool_transforms_reject_unsupported_fields():
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        MCPSettings(
            tool_transforms={
                "read_thing_messages": {
                    "description": "Read telemetry.",
                    "enabled": False,
                }
            }
        )


@pytest.mark.asyncio
async def test_apply_tool_transforms_updates_tool_metadata():
    server = FastMCP("test")

    @server.tool(description="Original description", title="Original Title")
    def sample_tool(value: str) -> str:
        return value

    settings = MCPSettings(
        tool_transforms={
            "sample_tool": {
                "description": "Deployment-specific description.",
                "title": "Deployment Title",
            }
        }
    )

    _apply_tool_transforms(server, settings)

    [tool] = await server.list_tools()
    assert tool.name == "sample_tool"
    assert tool.description == "Deployment-specific description."
    assert tool.title == "Deployment Title"


@pytest.mark.asyncio
async def test_disabled_tools_still_hide_transformed_tools():
    server = FastMCP("test")

    @server.tool(description="Original description")
    def sample_tool(value: str) -> str:
        return value

    settings = MCPSettings(
        disabled_tools=["sample_tool"],
        tool_transforms={
            "sample_tool": {"description": "Hidden deployment description."}
        },
    )

    _apply_tool_transforms(server, settings)
    server.disable(names=set(settings.disabled_tools), components={"tool"})

    assert await server.list_tools() == []
