from pydantic import Field

from connhex_mcp.client import ConnhexClient
from connhex_mcp.utils.schemas import ConnhexBaseModel


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


class ModelsService:
    def __init__(self, client: ConnhexClient):
        self.client = client

    async def get(self, model_id: str, headers: dict) -> dict:
        resp = await self.client.request(
            "GET", f"/iot/models/{model_id}", headers
        )
        return resp.json()

    async def list(
        self,
        headers: dict,
        *,
        limit: int = 10,
        offset: int = 0,
        name: str | None = None,
        order: str | None = None,
        dir: str | None = None,
        tag: str | None = None,
        tenant: str | None = None,
    ) -> dict:
        params: dict = {"limit": limit, "offset": offset}
        if name is not None:
            params["name"] = name
        if order is not None:
            params["order"] = order
        if dir is not None:
            params["dir"] = dir
        if tag is not None:
            params["tag"] = tag
        if tenant is not None:
            params["tenant"] = tenant
        resp = await self.client.request(
            "GET", "/iot/models", headers, params=params
        )
        return resp.json()

    async def get_things(
        self,
        model_id: str,
        headers: dict,
        *,
        limit: int = 10,
        offset: int = 0,
        order: str | None = None,
        dir: str | None = None,
    ) -> dict:
        params: dict = {"limit": limit, "offset": offset}
        if order is not None:
            params["order"] = order
        if dir is not None:
            params["dir"] = dir
        resp = await self.client.request(
            "GET", f"/iot/models/{model_id}/things", headers, params=params
        )
        return resp.json()
