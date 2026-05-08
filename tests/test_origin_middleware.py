from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from connhex_mcp.middleware import OriginValidationMiddleware


async def _ok(request: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def _make_client(allowed_origin: str) -> TestClient:
    app = Starlette(
        routes=[Route("/", _ok, methods=["GET", "POST"])],
        middleware=[],
    )
    app.add_middleware(
        OriginValidationMiddleware, allowed_origin=allowed_origin
    )
    return TestClient(app, raise_server_exceptions=True)


def test_no_origin_passes():
    client = _make_client("https://example.com")
    assert client.get("/").status_code == 200


def test_matching_origin_passes():
    client = _make_client("https://example.com")
    assert (
        client.get("/", headers={"Origin": "https://example.com"}).status_code
        == 200
    )


def test_mismatched_origin_blocked():
    client = _make_client("https://example.com")
    assert (
        client.get("/", headers={"Origin": "https://evil.com"}).status_code
        == 403
    )


def test_origin_path_stripped():
    """Only scheme+host are compared; paths on public_url don't break matching."""
    client = _make_client("https://example.com/some/path")
    assert (
        client.get("/", headers={"Origin": "https://example.com"}).status_code
        == 200
    )


def test_subdomain_blocked():
    """Subdomains are not implicitly allowed."""
    client = _make_client("https://example.com")
    assert (
        client.get(
            "/", headers={"Origin": "https://sub.example.com"}
        ).status_code
        == 403
    )
