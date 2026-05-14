from connhex._base_client import ConnhexClient


class IAMService:
    def __init__(self, client: ConnhexClient):
        self.client = client

    async def whoami(self) -> dict:
        resp = await self.client.request(
            "GET", "/auth/sessions/whoami", base="accounts"
        )
        return resp.json()

    async def get_identity_schemas(self) -> list:
        resp = await self.client.request(
            "GET", "/auth/schemas", base="accounts"
        )
        return resp.json()
