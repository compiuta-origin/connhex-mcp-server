from typing import Any, Literal

from pydantic import Field

from connhex.schemas import ConnhexBaseModel

DecimationFunc = Literal["max", "min", "avg", "sum", "stddev", "variance"]
DecimationType = Literal["v", "vb"]
ReadFormat = Literal["messages", "params", "infos", "metrics"]


class JSONMessage(ConnhexBaseModel):
    channel: str
    publisher: str
    payload: Any  # required — distinguishes JSON from SenML messages
    protocol: str | None = None
    time: str | None = None
    created: int | None = None
    id: str | None = None
    subtopic: str | None = None


class SenMLMessage(ConnhexBaseModel):
    channel: str
    publisher: str
    protocol: str | None = None
    name: str | None = None
    unit: str | None = None
    value: float | None = None
    string_value: str | None = Field(None, alias="stringValue")
    bool_value: bool | None = Field(None, alias="boolValue")
    data_value: str | None = Field(None, alias="dataValue")
    value_sum: float | None = Field(None, alias="valueSum")
    time: float | None = None
    update_time: float | None = Field(None, alias="updateTime")


class MessagesPage(ConnhexBaseModel):
    total: float
    offset: float
    limit: float
    messages: list[JSONMessage | SenMLMessage] = []
