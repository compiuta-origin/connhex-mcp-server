"""Authentication credentials for Connhex API clients."""

from dataclasses import dataclass


@dataclass(frozen=True)
class BearerAuth:
    """Authenticate requests with a bearer token."""

    token: str


@dataclass(frozen=True)
class SessionCookieAuth:
    """Authenticate requests with a Connhex ``chx_auth_session`` cookie."""

    value: str


Auth = BearerAuth | SessionCookieAuth
