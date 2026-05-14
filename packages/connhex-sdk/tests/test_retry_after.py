"""Tests for the Retry-After header parser."""

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx
from connhex._base_client import _retry_after_seconds


def _resp(headers: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(429, headers=headers or {})


def test_missing_header_returns_none():
    assert _retry_after_seconds(_resp()) is None


def test_empty_header_returns_none():
    assert _retry_after_seconds(_resp({"Retry-After": ""})) is None


def test_integer_seconds():
    assert _retry_after_seconds(_resp({"Retry-After": "5"})) == 5.0


def test_float_seconds_accepted():
    # Spec says delta-seconds is an integer, but tolerating floats is harmless.
    assert _retry_after_seconds(_resp({"Retry-After": "1.5"})) == 1.5


def test_negative_seconds_clamped_to_zero():
    assert _retry_after_seconds(_resp({"Retry-After": "-3"})) == 0.0


def test_http_date_in_future():
    future = datetime.now(timezone.utc) + timedelta(seconds=30)
    header = format_datetime(future, usegmt=True)
    delay = _retry_after_seconds(_resp({"Retry-After": header}))
    assert delay is not None
    assert 28.0 <= delay <= 31.0


def test_http_date_in_past_clamped_to_zero():
    past = datetime.now(timezone.utc) - timedelta(seconds=60)
    header = format_datetime(past, usegmt=True)
    assert _retry_after_seconds(_resp({"Retry-After": header})) == 0.0


def test_malformed_header_returns_none():
    assert _retry_after_seconds(_resp({"Retry-After": "not-a-date"})) is None
