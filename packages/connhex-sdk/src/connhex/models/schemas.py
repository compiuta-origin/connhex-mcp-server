from pydantic import Field

from connhex.schemas import ConnhexBaseModel


class Model(ConnhexBaseModel):
    id: str = Field(description="Unique model identifier (UUID).")
    name: str | None = Field(
        default=None, description="Human-readable model name."
    )
    description: str | None = Field(
        default=None, description="Free-form model description."
    )
    metadata: dict | None = Field(
        default=None, description="Arbitrary JSON metadata."
    )
    tags: list[str] | None = Field(
        default=None, description="Tags associated with the model."
    )
    tenants: list[str] | None = Field(
        default=None, description="Tenants that can access this model."
    )
    image: str | None = Field(default=None, description="URL to model image.")
    created_at: str | None = Field(
        default=None, description="ISO-8601 creation timestamp."
    )
    updated_at: str | None = Field(
        default=None, description="ISO-8601 last-updated timestamp."
    )


class ModelsPage(ConnhexBaseModel):
    models: list[Model]
    total: int | None = Field(
        default=None, description="Total number of matching models."
    )
    offset: int | None = Field(
        default=None, description="Number of items skipped."
    )
    limit: int | None = Field(default=None, description="Page size used.")
