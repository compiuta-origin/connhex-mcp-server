from connhex_mcp.client import ConnhexClient


class ThingsService:
    def __init__(self, client: ConnhexClient):
        self.client = client

    async def get(self, thing_id: str, headers: dict) -> dict:
        """
        Fetch a thing by its Connhex ID.

        Returns the full thing object including `metadata`, which contains
        `event_channel_id` and `control_channel_id` for IoT devices/edges.
        """
        resp = await self.client.request(
            "GET",
            f"/iot/things/{thing_id}",
            headers,
        )
        return resp.json()
