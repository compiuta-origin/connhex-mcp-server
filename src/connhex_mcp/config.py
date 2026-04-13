from enum import Enum

from pydantic import Field, HttpUrl
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

    @property
    def accounts_url(self) -> str:
        return f"{self.instance_url.scheme}://accounts.{self.instance_url.host}"

    @property
    def apis_url(self) -> str:
        return f"{self.instance_url.scheme}://apis.{self.instance_url.host}"
