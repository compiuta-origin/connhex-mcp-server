from connhex._base_client import ConnhexClient
from connhex.models.schemas import Model, ModelsPage
from connhex.things.schemas import ThingsPage


class ModelsService:
    def __init__(self, client: ConnhexClient):
        self.client = client

    async def get(self, model_id: str) -> Model:
        resp = await self.client.request("GET", f"/iot/models/{model_id}")
        return Model.model_validate(resp.json())

    async def list(
        self,
        *,
        limit: int = 10,
        offset: int = 0,
        name: str | None = None,
        order: str | None = None,
        dir: str | None = None,
        tag: str | None = None,
        tenant: str | None = None,
    ) -> ModelsPage:
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
        resp = await self.client.request("GET", "/iot/models", params=params)
        return ModelsPage.model_validate(resp.json())

    async def get_things(
        self,
        model_id: str,
        *,
        limit: int = 10,
        offset: int = 0,
        order: str | None = None,
        dir: str | None = None,
    ) -> ThingsPage:
        params: dict = {"limit": limit, "offset": offset}
        if order is not None:
            params["order"] = order
        if dir is not None:
            params["dir"] = dir
        resp = await self.client.request(
            "GET", f"/iot/models/{model_id}/things", params=params
        )
        return ThingsPage.model_validate(resp.json())
