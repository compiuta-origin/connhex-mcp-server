"""Build per-service Connhex URLs from a single instance URL."""

from urllib.parse import urlsplit


def _parts(instance_url: str) -> tuple[str, str]:
    parts = urlsplit(instance_url.rstrip("/"))
    if not parts.scheme or not parts.hostname:
        raise ValueError(f"invalid instance_url: {instance_url!r}")
    return parts.scheme, parts.hostname


def apis_url(instance_url: str) -> str:
    scheme, host = _parts(instance_url)
    return f"{scheme}://apis.{host}"


def accounts_url(instance_url: str) -> str:
    scheme, host = _parts(instance_url)
    return f"{scheme}://accounts.{host}"


def base_url(instance_url: str, base: str) -> str:
    if base == "apis":
        return apis_url(instance_url)
    if base == "accounts":
        return accounts_url(instance_url)
    raise ValueError(f"unknown base {base!r}")
