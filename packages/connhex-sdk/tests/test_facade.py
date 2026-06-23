"""Tests for the AsyncConnhex top-level facade."""

import connhex
import httpx
import pytest
from connhex import (
    APIConnectionError,
    APITimeoutError,
    AsyncConnhex,
    BearerAuth,
    AuthenticationError,
    ConflictError,
    ConnhexAPIError,
    ConnhexError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    SessionCookieAuth,
    UnprocessableEntityError,
)
from connhex.aio.services.iam import IAMService
from connhex.aio.services.models import ModelsService
from connhex.aio.services.provision import ProvisionService
from connhex.aio.services.reader import ReaderService
from connhex.aio.services.resources import ResourcesService
from connhex.aio.services.rules_engine import RulesEngineService
from connhex.aio.services.things import ThingsService
from connhex.urls import DEFAULT_INSTANCE_URL


def _facade(handler) -> AsyncConnhex:
    client = AsyncConnhex(instance_url="https://example.test", token="t")
    client._http._http = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
    )
    return client


def test_top_level_exports():
    assert AsyncConnhex is connhex.AsyncConnhex
    assert BearerAuth is connhex.BearerAuth
    assert SessionCookieAuth is connhex.SessionCookieAuth
    assert ConnhexAPIError is connhex.ConnhexAPIError
    assert ConnhexError is connhex.ConnhexError
    assert AuthenticationError is connhex.AuthenticationError
    assert PermissionDeniedError is connhex.PermissionDeniedError
    assert NotFoundError is connhex.NotFoundError
    assert ConflictError is connhex.ConflictError
    assert UnprocessableEntityError is connhex.UnprocessableEntityError
    assert RateLimitError is connhex.RateLimitError
    assert InternalServerError is connhex.InternalServerError
    assert APIConnectionError is connhex.APIConnectionError
    assert APITimeoutError is connhex.APITimeoutError
    assert isinstance(connhex.__version__, str)


def test_service_attributes_present_and_typed():
    c = AsyncConnhex(instance_url="https://example.test", token="t")
    assert isinstance(c.things, ThingsService)
    assert isinstance(c.models, ModelsService)
    assert isinstance(c.rules, RulesEngineService)
    assert isinstance(c.iam, IAMService)
    assert isinstance(c.reader, ReaderService)
    assert isinstance(c.provision, ProvisionService)
    assert isinstance(c.resources, ResourcesService)
    assert isinstance(c.manufacturing, ResourcesService)
    assert c.resources.base_url == "resources"
    assert c.manufacturing.base_url == "manufacturing"


def test_services_share_underlying_client():
    c = AsyncConnhex(instance_url="https://example.test", token="t")
    assert c.things.client is c._http
    assert c.models.client is c._http
    assert c.resources.client is c._http


@pytest.mark.asyncio
async def test_round_trip_through_facade():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "accounts.example.test"
        assert request.url.path == "/auth/sessions/whoami"
        return httpx.Response(200, json={"identity": {"id": "abc"}})

    client = _facade(handler)
    result = await client.iam.whoami()
    assert result == {"identity": {"id": "abc"}}
    await client.close()


@pytest.mark.asyncio
async def test_auth_provider_sends_session_cookie_only():
    async def auth_provider():
        return SessionCookieAuth("session-value")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["cookie"] == "chx_auth_session=session-value"
        assert "authorization" not in request.headers
        return httpx.Response(200, json={"identity": {"id": "abc"}})

    client = AsyncConnhex(
        instance_url="https://example.test", auth_provider=auth_provider
    )
    client._http._http = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=True
    )

    await client.iam.whoami()
    await client.close()


def test_env_fallback_instance_url_and_token(monkeypatch):
    monkeypatch.setenv("CONNHEX_INSTANCE_URL", "https://env.example.test")
    monkeypatch.setenv("CONNHEX_BEARER_TOKEN", "env-tok")
    c = AsyncConnhex()
    assert c._http.instance_url == "https://env.example.test"
    assert c._http._token == "env-tok"


def test_explicit_args_override_env(monkeypatch):
    monkeypatch.setenv("CONNHEX_INSTANCE_URL", "https://env.example.test")
    monkeypatch.setenv("CONNHEX_BEARER_TOKEN", "env-tok")
    c = AsyncConnhex(instance_url="https://arg.example.test", token="arg-tok")
    assert c._http.instance_url == "https://arg.example.test"
    assert c._http._token == "arg-tok"


def test_default_instance_url(monkeypatch):
    monkeypatch.delenv("CONNHEX_INSTANCE_URL", raising=False)
    c = AsyncConnhex(token="t")
    assert c._http.instance_url == DEFAULT_INSTANCE_URL


def test_auth_modes_are_mutually_exclusive():
    async def auth_provider():
        return BearerAuth("token")

    with pytest.raises(ValueError):
        AsyncConnhex(
            instance_url="https://example.test",
            token="token",
            auth_provider=auth_provider,
        )


@pytest.mark.asyncio
async def test_async_context_manager_closes_http():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    client = _facade(handler)
    async with client as c:
        assert c is client
        assert not c._http._http.is_closed
    assert client._http._http.is_closed
