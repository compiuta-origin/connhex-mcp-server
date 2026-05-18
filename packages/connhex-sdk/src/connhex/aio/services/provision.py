from connhex.aio._base_client import ConnhexClient
from connhex.schemas.provision import BulkResult, ProvisionData


class ProvisionService:
    def __init__(self, client: ConnhexClient):
        self.client = client

    async def bulk_provision(self, items: list[ProvisionData]) -> BulkResult:
        payload = [item.model_dump(exclude_none=True) for item in items]
        resp = await self.client.request(
            "POST",
            "/iot/provision/things/bulk",
            json=payload,
            extra_headers={"Content-Type": "application/json"},
        )
        return BulkResult.model_validate(resp.json())

    async def bulk_unprovision(self, thing_ids: list[str]) -> None:
        await self.client.request(
            "DELETE",
            "/iot/provision/things/bulk",
            json=thing_ids,
            extra_headers={"Content-Type": "application/json"},
        )
