"""Tests for ConnhexClient retry and timeout behavior."""

from itertools import count

import httpx
import pytest

from connhex_sdk.client import ConnhexClient
from connhex_sdk.errors import ConnhexAPIError


def _make_client(monkeypatch, handler, *, max_retries=2, **kwargs):
    """Build a ConnhexClient whose internal AsyncClient uses MockTransport.

    Sleeps are patched to 0 so retry tests run instantly; the recorded
    delays are returned to the caller via the `sleeps` list.
    """
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr("connhex_sdk.client.asyncio.sleep", fake_sleep)

    client = ConnhexClient(
        instance_url="https://example.test",
        token="t",
        max_retries=max_retries,
        retry_initial=0.5,
        retry_cap=8.0,
        **kwargs,
    )
    client._http = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        follow_redirects=True,
    )
    return client, sleeps


@pytest.mark.asyncio
async def test_success_first_try_no_retry(monkeypatch):
    calls = count()

    def handler(request: httpx.Request) -> httpx.Response:
        next(calls)
        return httpx.Response(200, json={"ok": True})

    client, sleeps = _make_client(monkeypatch, handler)
    resp = await client.request("GET", "/x")
    assert resp.status_code == 200
    assert sleeps == []
    await client.close()


@pytest.mark.asyncio
async def test_retries_on_500_then_succeeds(monkeypatch):
    attempts = count()

    def handler(request: httpx.Request) -> httpx.Response:
        n = next(attempts)
        if n == 0:
            return httpx.Response(500, json={"errors": [{"detail": "boom"}]})
        return httpx.Response(200, json={"ok": True})

    client, sleeps = _make_client(monkeypatch, handler)
    resp = await client.request("GET", "/x")
    assert resp.status_code == 200
    assert len(sleeps) == 1
    await client.close()


@pytest.mark.asyncio
async def test_exhausts_retries_raises(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"errors": [{"detail": "down"}]})

    client, sleeps = _make_client(monkeypatch, handler, max_retries=2)
    with pytest.raises(ConnhexAPIError) as ei:
        await client.request("GET", "/x")
    assert ei.value.status == 503
    assert len(sleeps) == 2
    await client.close()


@pytest.mark.asyncio
async def test_retry_after_header_honored(monkeypatch):
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
    await client.request("GET", "/x")
    assert sleeps == [3.0]
    await client.close()


@pytest.mark.asyncio
async def test_network_error_retried_then_succeeds(monkeypatch):
    attempts = count()

    def handler(request: httpx.Request) -> httpx.Response:
        if next(attempts) == 0:
            raise httpx.ConnectError("nope", request=request)
        return httpx.Response(200, json={"ok": True})

    client, sleeps = _make_client(monkeypatch, handler)
    resp = await client.request("GET", "/x")
    assert resp.status_code == 200
    assert len(sleeps) == 1
    await client.close()


@pytest.mark.asyncio
async def test_non_retryable_4xx_raises_immediately(monkeypatch):
    attempts = count()

    def handler(request: httpx.Request) -> httpx.Response:
        next(attempts)
        return httpx.Response(400, json={"errors": [{"detail": "bad"}]})

    client, sleeps = _make_client(monkeypatch, handler)
    with pytest.raises(ConnhexAPIError) as ei:
        await client.request("GET", "/x")
    assert ei.value.status == 400
    assert sleeps == []
    await client.close()


@pytest.mark.asyncio
async def test_max_retries_zero_disables_retry(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"errors": [{"detail": "x"}]})

    client, sleeps = _make_client(monkeypatch, handler, max_retries=0)
    with pytest.raises(ConnhexAPIError) as ei:
        await client.request("GET", "/x")
    assert ei.value.status == 503
    assert sleeps == []
    await client.close()


@pytest.mark.asyncio
async def test_per_request_timeout_override(monkeypatch):
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["timeout"] = request.extensions.get("timeout")
        return httpx.Response(200, json={"ok": True})

    client, _ = _make_client(monkeypatch, handler)
    await client.request("GET", "/x", timeout=1.5)
    timeout_ext = seen["timeout"]
    assert isinstance(timeout_ext, dict)
    assert timeout_ext.get("connect") == 1.5
    await client.close()


@pytest.mark.asyncio
async def test_user_agent_header_set(monkeypatch):
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["ua"] = request.headers.get("User-Agent", "")
        return httpx.Response(200, json={"ok": True})

    client, _ = _make_client(monkeypatch, handler)
    await client.request("GET", "/x")
    assert seen["ua"].startswith("connhex-python/")
    assert "httpx/" in seen["ua"]
    await client.close()
