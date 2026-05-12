from connhex_sdk.config import CoreSettings
from pydantic import Field, field_validator


class MCPSettings(CoreSettings):
    public_url: str | None = Field(
        default=None,
        description="Public base URL, required for remote mode",
    )
    log_config_path: str | None = Field(
        default=None, description="Path to logging config JSON"
    )
    disabled_tools: list[str] | None = Field(
        default=None, description="Tool names to hide from the LLM"
    )

    @field_validator("disabled_tools", mode="before")
    @classmethod
    def parse_comma_separated(cls, v: object) -> object:
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v
