from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class CoreSettings(BaseSettings):
    """Minimal Connhex connection settings.

    Carries only the instance URL. Auth (tokens, credentials) and any
    auxiliary configuration belong to consumer-side settings classes.
    """

    model_config = SettingsConfigDict(env_prefix="CONNHEX_", extra="ignore")

    instance_url: HttpUrl = Field(..., description="Connhex instance URL")
