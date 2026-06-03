"""Tests for the sync Connhex top-level facade."""

import connhex
import httpx
import pytest
from connhex import Connhex, ConnhexAPIError
from connhex.sync.services.iam import IAMService
from connhex.sync.services.models import ModelsService
from connhex.sync.services.provision import ProvisionService
from connhex.sync.services.reader import ReaderService
from connhex.sync.services.resources import ResourcesService
from connhex.sync.services.rules_engine import RulesEngineService
from connhex.sync.services.things import ThingsService
from connhex.urls import DEFAULT_INSTANCE_URL


def _facade(handler) -> Connhex:
    client = Connhex(instance_url="https://example.test", token="t")
    client._http._http = httpx.Client(
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
    )
    return client


def test_top_level_exports():
    assert Connhex is connhex.Connhex
    assert ConnhexAPIError is connhex.ConnhexAPIError


def test_service_attributes_present_and_typed():
    c = Connhex(instance_url="https://example.test", token="t")
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
    c = Connhex(instance_url="https://example.test", token="t")
    assert c.things.client is c._http
    assert c.models.client is c._http
    assert c.resources.client is c._http


def test_round_trip_through_facade():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "accounts.example.test"
        assert request.url.path == "/auth/sessions/whoami"
        return httpx.Response(200, json={"identity": {"id": "abc"}})

    client = _facade(handler)
    result = client.iam.whoami()
    assert result == {"identity": {"id": "abc"}}
    client.close()


def test_things_list_smoke():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "apis.example.test"
        assert request.url.path == "/iot/things"
        return httpx.Response(
            200,
            json={"things": [], "total": 0, "limit": 10, "offset": 0},
        )

    client = _facade(handler)
    page = client.things.list(limit=10)
    assert page.total == 0
    assert page.things == []
    client.close()


def test_env_fallback_instance_url_and_token(monkeypatch):
    monkeypatch.setenv("CONNHEX_INSTANCE_URL", "https://env.example.test")
    monkeypatch.setenv("CONNHEX_BEARER_TOKEN", "env-tok")
    c = Connhex()
    assert c._http.instance_url == "https://env.example.test"
    assert c._http._token == "env-tok"


def test_default_instance_url(monkeypatch):
    monkeypatch.delenv("CONNHEX_INSTANCE_URL", raising=False)
    c = Connhex(token="t")
    assert c._http.instance_url == DEFAULT_INSTANCE_URL


def test_token_and_token_provider_mutually_exclusive():
    with pytest.raises(ValueError):
        Connhex(
            instance_url="https://example.test",
            token="t",
            token_provider=lambda: "x",
        )


def test_sync_context_manager_closes_http():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    client = _facade(handler)
    with client as c:
        assert c is client
        assert not c._http._http.is_closed
    assert client._http._http.is_closed
