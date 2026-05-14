"""Tests for the AsyncConnhex top-level facade."""

import httpx
import pytest

import connhex_sdk
from connhex_sdk import AsyncConnhex, ConnhexAPIError
from connhex_sdk.iam import IAMService
from connhex_sdk.models import ModelsService
from connhex_sdk.provision import ProvisionService
from connhex_sdk.reader import ReaderService
from connhex_sdk.resources import ResourcesService
from connhex_sdk.rules_engine import RulesEngineService
from connhex_sdk.things import ThingsService


def _facade(handler) -> AsyncConnhex:
    client = AsyncConnhex(instance_url="https://example.test", token="t")
    client._http._http = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
    )
    return client


def test_top_level_exports():
    assert AsyncConnhex is connhex_sdk.AsyncConnhex
    assert ConnhexAPIError is connhex_sdk.ConnhexAPIError
    assert isinstance(connhex_sdk.__version__, str)


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


def test_missing_instance_url_raises(monkeypatch):
    monkeypatch.delenv("CONNHEX_INSTANCE_URL", raising=False)
    with pytest.raises(ValueError, match="instance_url is required"):
        AsyncConnhex(token="t")


@pytest.mark.asyncio
async def test_async_context_manager_closes_http():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    client = _facade(handler)
    async with client as c:
        assert c is client
        assert not c._http._http.is_closed
    assert client._http._http.is_closed
