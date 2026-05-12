from connhex_sdk.client import ConnhexClient
from connhex_sdk.reader.schemas import (
    DecimationFunc,
    DecimationType,
    MessagesPage,
    ReadFormat,
)


class ReaderService:
    def __init__(self, client: ConnhexClient):
        self.client = client

    async def read_messages(
        self,
        channel_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
        from_s: float | None = None,
        to_s: float | None = None,
        publisher: str | None = None,
        name: str | None = None,
        format: ReadFormat = "messages",
        ds: str | None = None,
        dsf: DecimationFunc | None = None,
        dsv: DecimationType | None = None,
    ) -> MessagesPage:
        """
        Read messages from a Connhex channel.

        See `GET /iot/reader/channels/{channel_id}/messages` upstream docs for
        full parameter semantics.
        """
        params: dict = {
            "limit": limit,
            "offset": offset,
            "format": format,
        }
        if from_s is not None:
            params["from"] = from_s
        if to_s is not None:
            params["to"] = to_s
        if publisher is not None:
            params["publisher"] = publisher
        if name is not None:
            params["name"] = name
        if ds is not None:
            params["ds"] = ds
        if dsf is not None:
            params["dsf"] = dsf
        if dsv is not None:
            params["dsv"] = dsv

        resp = await self.client.request(
            "GET",
            f"/iot/reader/channels/{channel_id}/messages",
            params=params,
        )
        return MessagesPage.model_validate(resp.json())
