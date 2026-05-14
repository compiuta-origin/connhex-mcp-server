from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CONNHEX_", extra="ignore")

    instance_url: HttpUrl = Field(..., description="Connhex instance URL")
    bearer_token: str | None = Field(
        default=None,
        description="Static bearer token (local mode fallback).",
    )
    username: str | None = Field(
        default=None,
        description="Username for password auth (local mode fallback).",
    )
    password: str | None = Field(
        default=None,
        description="Password for password auth (local mode fallback).",
    )
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
