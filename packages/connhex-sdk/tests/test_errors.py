import httpx
import pytest
from connhex.errors import (
    AuthenticationError,
    ConflictError,
    ConnhexAPIError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
    raise_for_connhex_response,
)


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (401, AuthenticationError),
        (403, PermissionDeniedError),
        (404, NotFoundError),
        (409, ConflictError),
        (422, UnprocessableEntityError),
        (429, RateLimitError),
        (500, InternalServerError),
        (503, InternalServerError),
        (400, ConnhexAPIError),
    ],
)
def test_http_statuses_map_to_typed_errors(status, error_type):
    response = httpx.Response(
        status,
        headers={"x-request-id": "req_123"},
        json={"errors": [{"detail": "bad request"}]},
    )

    with pytest.raises(error_type) as ei:
        raise_for_connhex_response(response)

    err = ei.value
    assert isinstance(err, ConnhexAPIError)
    assert err.status == status
    assert err.detail == "bad request"
    assert err.errors == [{"detail": "bad request"}]
    assert err.response is response
    assert err.request_id == "req_123"


def test_ory_error_message_is_used_when_jsonapi_errors_are_absent():
    response = httpx.Response(
        401,
        json={"error": {"message": "session expired"}},
    )

    with pytest.raises(AuthenticationError) as ei:
        raise_for_connhex_response(response)

    assert ei.value.detail == "session expired"
    assert ei.value.errors == []


def test_non_json_error_uses_response_text():
    response = httpx.Response(502, text="gateway exploded")

    with pytest.raises(InternalServerError) as ei:
        raise_for_connhex_response(response)

    assert ei.value.detail == "gateway exploded"


def test_success_response_does_not_raise():
    raise_for_connhex_response(httpx.Response(204))
