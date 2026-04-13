from connhex_mcp.client import ConnhexClient


class IAMService:
    def __init__(self, client: ConnhexClient):
        self.client = client

    async def whoami(self, headers: dict) -> dict:
        resp = await self.client.request(
            "GET",
            "/auth/sessions/whoami",
            headers,
            base="accounts",
        )
        return resp.json()
