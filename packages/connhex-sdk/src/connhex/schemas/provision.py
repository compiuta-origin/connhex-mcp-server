from uuid import UUID, uuid4

from pydantic import Field, field_validator, model_validator

from connhex.schemas._base import ConnhexBaseModel


class ProvisionData(ConnhexBaseModel):
    init_id: str = Field(
        description="External identifier (MAC address, serial number or similar)."
    )
    init_key: str = Field(
        default_factory=lambda: str(uuid4()),
        description="External key. Auto-generated UUID when omitted.",
    )
    name: str | None = Field(default=None)
    model: str | None = Field(
        default=None, description="UUID of the device model."
    )
    tenant: str | None = Field(default=None)
    migration_key: str | None = Field(default=None)
    migration_key_quota: int | None = Field(default=None)

    @field_validator("init_id")
    @classmethod
    def _init_id_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("init_id must be a non-empty string")
        return v

    @field_validator("model")
    @classmethod
    def _model_is_uuid(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        try:
            UUID(v)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"model must be a valid UUID: {e}") from e
        return v

    @model_validator(mode="before")
    @classmethod
    def _coerce_quota(cls, data: object) -> object:
        if isinstance(data, dict):
            quota = data.get("migration_key_quota")
            if isinstance(quota, str) and quota.strip():
                data = {**data, "migration_key_quota": int(quota)}
        return data


class ProvisionedThing(ConnhexBaseModel):
    id: str
    name: str | None = None
    key: str | None = None
    metadata: dict | None = None
    tenant: str | None = None
    model: str | None = None


class BulkResult(ConnhexBaseModel):
    things: list[ProvisionedThing] = Field(default_factory=list)
    processed: int | None = None
    failed: int | None = None
    errors: list[str] = Field(default_factory=list)

    @field_validator("things", "errors", mode="before")
    @classmethod
    def _none_to_empty(cls, v: object) -> object:
        return v if v is not None else []
