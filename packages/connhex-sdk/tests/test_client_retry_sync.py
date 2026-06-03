"""Tests for the sync ConnhexClient retry and timeout behavior."""

from itertools import count

import httpx
import pytest
from connhex.errors import (
    APIConnectionError,
    APITimeoutError,
    ConnhexAPIError,
    ConnhexError,
)
from connhex.sync._base_client import ConnhexClient


def _make_client(monkeypatch, handler, *, max_retries=2, **kwargs):
    sleeps: list[float] = []

    def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr("connhex.sync._base_client._sleep", fake_sleep)

    client = ConnhexClient(
        instance_url="https://example.test",
        token="t",
        max_retries=max_retries,
        retry_initial=0.5,
        retry_cap=8.0,
        **kwargs,
    )
    client._http = httpx.Client(
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
    )
    return client, sleeps


def test_success_first_try_no_retry(monkeypatch):
    calls = count()

    def handler(request: httpx.Request) -> httpx.Response:
        next(calls)
        return httpx.Response(200, json={"ok": True})

    client, sleeps = _make_client(monkeypatch, handler)
    resp = client.request("GET", "/x")
    assert resp.status_code == 200
    assert sleeps == []
    client.close()


def test_retries_on_500_then_succeeds(monkeypatch):
    attempts = count()

    def handler(request: httpx.Request) -> httpx.Response:
        n = next(attempts)
        if n == 0:
            return httpx.Response(500, json={"errors": [{"detail": "boom"}]})
        return httpx.Response(200, json={"ok": True})

    client, sleeps = _make_client(monkeypatch, handler)
    resp = client.request("GET", "/x")
    assert resp.status_code == 200
    assert len(sleeps) == 1
    client.close()


def test_exhausts_retries_raises(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"errors": [{"detail": "down"}]})

    client, sleeps = _make_client(monkeypatch, handler, max_retries=2)
    with pytest.raises(ConnhexAPIError) as ei:
        client.request("GET", "/x")
    assert ei.value.status == 503
    assert len(sleeps) == 2
    client.close()


def test_retry_after_header_honored(monkeypatch):
    attempts = count()

    def handler(request: httpx.Request) -> httpx.Response:
        if next(attempts) == 0:
            return httpx.Response(
                429,
                headers={"Retry-After": "3"},
                json={"errors": [{"detail": "slow"}]},
            )
        return httpx.Response(200, json={"ok": True})

    client, sleeps = _make_client(monkeypatch, handler)
    client.request("GET", "/x")
    assert sleeps == [3.0]
    client.close()


def test_network_error_retried_then_succeeds(monkeypatch):
    attempts = count()

    def handler(request: httpx.Request) -> httpx.Response:
        if next(attempts) == 0:
            raise httpx.ConnectError("nope", request=request)
        return httpx.Response(200, json={"ok": True})

    client, sleeps = _make_client(monkeypatch, handler)
    resp = client.request("GET", "/x")
    assert resp.status_code == 200
    assert len(sleeps) == 1
    client.close()


def test_network_error_exhausts_retries(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nope", request=request)

    client, sleeps = _make_client(monkeypatch, handler, max_retries=1)
    with pytest.raises(APIConnectionError) as ei:
        client.request("GET", "/x")
    assert isinstance(ei.value, ConnhexError)
    assert not isinstance(ei.value, ConnhexAPIError)
    assert isinstance(ei.value.cause, httpx.ConnectError)
    assert len(sleeps) == 1
    client.close()


def test_timeout_error_exhausts_retries(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    client, sleeps = _make_client(monkeypatch, handler, max_retries=1)
    with pytest.raises(APITimeoutError) as ei:
        client.request("GET", "/x")
    assert isinstance(ei.value, APIConnectionError)
    assert isinstance(ei.value.cause, httpx.ReadTimeout)
    assert len(sleeps) == 1
    client.close()


def test_max_retries_zero_disables_retry(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"errors": [{"detail": "x"}]})

    client, sleeps = _make_client(monkeypatch, handler, max_retries=0)
    with pytest.raises(ConnhexAPIError) as ei:
        client.request("GET", "/x")
    assert ei.value.status == 503
    assert sleeps == []
    client.close()


def test_user_agent_header_set(monkeypatch):
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["ua"] = request.headers.get("User-Agent", "")
        return httpx.Response(200, json={"ok": True})

    client, _ = _make_client(monkeypatch, handler)
    client.request("GET", "/x")
    assert seen["ua"].startswith("connhex-python/")
    assert "httpx/" in seen["ua"]
    client.close()
