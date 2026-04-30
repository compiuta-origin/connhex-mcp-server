from enum import Enum

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthType(str, Enum):
    CREDENTIALS = "credentials"
    TOKEN = "token"
    SESSION = "session"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CONNHEX_")

    instance_url: HttpUrl = Field(..., description="Connhex instance URL")

    auth_type: AuthType = Field(
        default=AuthType.CREDENTIALS, description="Authentication strategy"
    )
    username: str | None = Field(
        default=None, description="For auth_type=credentials"
    )
    password: str | None = Field(
        default=None, description="For auth_type=credentials"
    )
    bearer_token: str | None = Field(
        default=None, description="For auth_type=token"
    )
    public_url: str | None = Field(
        default=None,
        description=("Public base URL, required for remote mode"),
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

    @property
    def accounts_url(self) -> str:
        return f"{self.instance_url.scheme}://accounts.{self.instance_url.host}"

    @property
    def apis_url(self) -> str:
        return f"{self.instance_url.scheme}://apis.{self.instance_url.host}"
