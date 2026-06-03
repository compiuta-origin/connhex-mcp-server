from typing import Literal

from connhex.urls import DEFAULT_INSTANCE_URL
from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class CLISettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CONNHEX_", extra="ignore")

    instance_url: HttpUrl = Field(
        default=DEFAULT_INSTANCE_URL,
        description="Connhex instance URL",
    )
    output: Literal["table", "json"] = "table"
    log_config: str | None = None
