from typing import Generic, TypeVar

from connhex_sdk.schemas import ConnhexBaseModel

T = TypeVar("T")


class Resource(ConnhexBaseModel):
    """A flattened JSON:API resource. All attributes are hoisted to top level."""

    id: str
    type: str


class ListResponse(ConnhexBaseModel, Generic[T]):
    """Wrapper for paginated JSON:API list responses (after flatten_response)."""

    data: list[T]
    total: int | None = None
    has_next: bool
