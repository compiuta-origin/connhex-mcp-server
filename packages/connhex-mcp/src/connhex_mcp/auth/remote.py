import asyncio
import logging
import secrets
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import httpx
from connhex_sdk.auth.kratos import KRATOS_TIMEOUT, kratos_password_login
from cryptography.fernet import Fernet
from fastmcp.server.auth.auth import AccessToken, OAuthProvider
from mcp.server.auth.provider import (
    AuthorizationCode,
    AuthorizationParams,
    TokenError,
    construct_redirect_uri,
)
from mcp.server.auth.settings import ClientRegistrationOptions
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response
from starlette.routing import Route

from connhex_mcp.auth.templates import render_error_page, render_login_page
from connhex_mcp.config import MCPSettings

logger = logging.getLogger(__name__)

FLOW_TTL = 300
CODE_TTL = 300
RENEWAL_IDLE_TTL = 7 * 24 * 60 * 60


_fernet = Fernet(Fernet.generate_key())


class StoredCredentials:
    """Stores credentials encrypted in memory to limit accidental exposure.

    Uses a process-local Fernet key so credentials are opaque in heap dumps
    and never appear in logs or tracebacks.

    Note: credentials are not persisted across restarts. Active Kratos sessions
    survive a restart (the client token is re-validated against Kratos), but
    auto-renewal capability is lost until the user next authenticates manually.

    # TODO: replace credential storage with OAuth refresh tokens
    """

    __slots__ = ("_identifier", "_password")

    def __repr__(self) -> str:
        return "<StoredCredentials>"

    __str__ = __repr__

    def __init__(self, identifier: str, password: str):
        self._identifier = _fernet.encrypt(identifier.encode())
        self._password = _fernet.encrypt(password.encode())

    def get(self) -> tuple[str, str]:
        return (
            _fernet.decrypt(self._identifier).decode(),
            _fernet.decrypt(self._password).decode(),
        )


def _now() -> float:
    return time.time()


@dataclass
class RenewalRecord:
    credentials: StoredCredentials
    current_token: str
    client_id: str
    last_used_at: float


class ConnhexOAuthProvider(OAuthProvider):
    """OAuth provider that authenticates users via Connhex.

    Implements the full OAuth 2.0 authorization code flow with PKCE.
    """

    def __init__(self, settings: MCPSettings):
        assert settings.public_url, (
            "CONNHEX_PUBLIC_URL is required for remote mode"
        )

        super().__init__(
            base_url=settings.public_url,
            client_registration_options=ClientRegistrationOptions(
                enabled=True,
            ),
        )

        self.settings = settings
        self.accounts_url = settings.accounts_url

        # In-memory stores
        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._auth_codes: dict[str, AuthorizationCode] = {}
        self._code_tokens: dict[str, str] = {}  # code -> ory_st_* token
        self._access_tokens: dict[str, AccessToken] = {}
        self._pending_flows: dict[str, dict] = {}
        self._renewal_records: dict[str, RenewalRecord] = {}
        self._token_records: dict[str, str] = {}
        self._token_forwarding: dict[
            str, str
        ] = {}  # expired token -> live token

        # Start background cleanup task
        self._cleanup_task: asyncio.Task | None = None

    def _create_renewal_record(
        self, token: str, credentials: StoredCredentials
    ) -> str:
        record_id = secrets.token_urlsafe(16)
        self._renewal_records[record_id] = RenewalRecord(
            credentials=credentials,
            current_token=token,
            client_id="",
            last_used_at=_now(),
        )
        self._token_records[token] = record_id
        return record_id

    def _get_record_for_token(
        self, token: str
    ) -> tuple[str, RenewalRecord] | None:
        record_id = self._token_records.get(token)
        if not record_id:
            return None
        record = self._renewal_records.get(record_id)
        if not record:
            self._token_records.pop(token, None)
            return None
        return record_id, record

    def _get_record_for_request_token(
        self, requested_token: str, live_token: str
    ) -> tuple[str, RenewalRecord] | None:
        return self._get_record_for_token(
            requested_token
        ) or self._get_record_for_token(live_token)

    def _remove_record(self, record_id: str) -> None:
        record = self._renewal_records.pop(record_id, None)
        if not record:
            return

        self._access_tokens.pop(record.current_token, None)

        tokens = [
            token
            for token, mapped_record_id in self._token_records.items()
            if mapped_record_id == record_id
        ]
        for token in tokens:
            self._token_records.pop(token, None)
            self._access_tokens.pop(token, None)
            self._token_forwarding.pop(token, None)

        stale_aliases = [
            token
            for token, live_token in self._token_forwarding.items()
            if live_token == record.current_token
        ]
        for token in stale_aliases:
            self._token_forwarding.pop(token, None)

    def _ensure_cleanup(self) -> None:
        """Start the cleanup task if not already running."""
        if self._cleanup_task is None or self._cleanup_task.done():
            try:
                loop = asyncio.get_running_loop()
                self._cleanup_task = loop.create_task(self._cleanup_loop())
                logger.info("Auth cleanup task started")
            except RuntimeError:
                pass  # No running loop yet, will start later

    async def _cleanup_loop(self) -> None:
        """Periodically clean up expired flows and codes."""
        while True:
            await asyncio.sleep(30)
            try:
                self._cleanup_once()
            except Exception:
                logger.warning("Error in auth cleanup loop", exc_info=True)

    def _cleanup_once(self) -> None:
        now = _now()

        expired_flows = [
            k
            for k, v in self._pending_flows.items()
            if v.get("expires_at", 0) < now
        ]
        for k in expired_flows:
            self._pending_flows.pop(k, None)

        expired_codes = [
            k for k, v in self._auth_codes.items() if (v.expires_at or 0) < now
        ]
        for k in expired_codes:
            self._auth_codes.pop(k, None)
            self._code_tokens.pop(k, None)

        expired_tokens = [
            k
            for k, v in self._access_tokens.items()
            if v.expires_at and v.expires_at < now
        ]
        for k in expired_tokens:
            self._access_tokens.pop(k, None)

        idle_record_ids = [
            record_id
            for record_id, record in self._renewal_records.items()
            if record.last_used_at < now - RENEWAL_IDLE_TTL
        ]
        for record_id in idle_record_ids:
            logger.info("Removing idle renewal state for record %s", record_id)
            self._remove_record(record_id)

    async def get_client(
        self, client_id: str
    ) -> OAuthClientInformationFull | None:
        return self._clients.get(client_id)

    async def register_client(
        self, client_info: OAuthClientInformationFull
    ) -> None:
        if client_info.client_id:
            self._clients[client_info.client_id] = client_info

    async def authorize(
        self,
        client: OAuthClientInformationFull,
        params: AuthorizationParams,
    ) -> str:
        """Store the pending flow and redirect to the login form."""
        self._ensure_cleanup()

        flow_id = secrets.token_urlsafe(32)
        self._pending_flows[flow_id] = {
            "client": client,
            "params": params,
            "expires_at": _now() + FLOW_TTL,
        }

        base = str(self.base_url).rstrip("/")
        return f"{base}/oauth/login?flow_id={flow_id}"

    async def load_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: str,
    ) -> AuthorizationCode | None:
        code_obj = self._auth_codes.get(authorization_code)
        if code_obj is None:
            return None
        if code_obj.client_id != client.client_id:
            return None
        if code_obj.expires_at and code_obj.expires_at < _now():
            self._auth_codes.pop(authorization_code, None)
            self._code_tokens.pop(authorization_code, None)
            return None
        return code_obj

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: AuthorizationCode,
    ) -> OAuthToken:
        """Exchange an authorization code for the ory_st_* session token."""
        code_str = authorization_code.code
        ory_token = self._code_tokens.pop(code_str, None)
        self._auth_codes.pop(code_str, None)

        if not ory_token:
            raise TokenError(
                error="invalid_grant",
                error_description="Authorization code not found or expired",
            )

        # Verify the session is still valid and get expiry
        expires_in = await self._get_session_ttl(ory_token)
        if expires_in is None:
            raise TokenError(
                error="invalid_grant",
                error_description="Session token is no longer valid",
            )

        # Store for load_access_token lookups
        self._access_tokens[ory_token] = AccessToken(
            token=ory_token,
            client_id=client.client_id or "",
            scopes=[],
            expires_at=int(_now() + expires_in),
        )
        record = self._get_record_for_token(ory_token)
        if record:
            _, renewal_record = record
            renewal_record.client_id = client.client_id or ""
            renewal_record.last_used_at = _now()

        logger.info("Token exchange complete for client %s", client.client_id)
        return OAuthToken(
            access_token=ory_token,
            token_type="Bearer",
            expires_in=expires_in,
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        """Verify token via Kratos whoami endpoint. Auto-renews if expired."""
        now = _now()
        live = self._token_forwarding.get(token, token)
        record_info = self._get_record_for_request_token(token, live)

        # Cache hit on the live token
        cached = self._access_tokens.get(live)
        if cached and cached.expires_at and cached.expires_at > now:
            if record_info:
                _, record = record_info
                record.last_used_at = now
            logger.debug("Access token cache hit")
            return cached

        # Verify live token with Kratos
        expires_in = await self._get_session_ttl(live)

        if expires_in is not None and expires_in > 0:
            client_id = cached.client_id if cached else ""
            if record_info:
                _, record = record_info
                record.last_used_at = now
                client_id = client_id or record.client_id
            access_token = AccessToken(
                token=live,
                client_id=client_id,
                scopes=[],
                expires_at=int(now + expires_in),
            )
            self._access_tokens[live] = access_token
            return access_token

        # Session expired — try auto-renewal if credentials are known
        if not record_info:
            logger.warning(
                "Access token expired and no credentials available for renewal"
            )
            self._access_tokens.pop(live, None)
            return None

        record_id, record = record_info
        identifier, password = record.credentials.get()
        logger.info(
            "Session expired — attempting auto-renewal for user %s", identifier
        )

        try:
            new_token = await kratos_password_login(
                self.accounts_url, identifier, password
            )
        except Exception:
            logger.warning(
                "Auto-renewal failed for user %s", identifier, exc_info=True
            )
            self._access_tokens.pop(live, None)
            return None

        new_expires_in = await self._get_session_ttl(new_token)
        if new_expires_in is None:
            logger.warning(
                "Renewed token failed Kratos validation for user %s", identifier
            )
            return None

        old_client_id = cached.client_id if cached else record.client_id

        self._token_forwarding[token] = new_token
        if live != token:
            self._token_forwarding[live] = new_token
        self._token_records[new_token] = record_id
        record.current_token = new_token
        record.client_id = old_client_id
        record.last_used_at = now

        new_access_token = AccessToken(
            token=new_token,
            client_id=old_client_id,
            scopes=[],
            expires_at=int(now + new_expires_in),
        )
        self._access_tokens[new_token] = new_access_token
        self._access_tokens.pop(live, None)

        logger.info(
            "Session auto-renewed for client %s (user %s)",
            old_client_id,
            identifier,
        )
        return new_access_token

    async def load_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: str,
    ):
        """Refresh tokens are not supported — sessions are long-lived."""
        return None

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token,
        scopes: list[str],
    ) -> OAuthToken:
        raise TokenError(
            error="unsupported_grant_type",
            error_description="Refresh tokens are not supported",
        )

    async def revoke_token(self, token) -> None:
        """Clear local renewal state. Session remains valid in Kratos."""
        token_str = token.token if hasattr(token, "token") else str(token)
        live = self._token_forwarding.get(token_str, token_str)
        record = self._get_record_for_request_token(token_str, live)
        if record:
            record_id, _ = record
            self._remove_record(record_id)
            return

        self._access_tokens.pop(token_str, None)
        self._access_tokens.pop(live, None)
        self._token_forwarding.pop(token_str, None)

    def get_routes(self, mcp_path: str | None = None) -> list[Route]:
        """Add login form and favicon routes to the standard OAuth routes."""
        routes = super().get_routes(mcp_path)

        routes.append(
            Route(
                "/oauth/login",
                endpoint=self._handle_login_page,
                methods=["GET"],
            )
        )
        routes.append(
            Route(
                "/oauth/login",
                endpoint=self._handle_login_submit,
                methods=["POST"],
            )
        )
        routes.append(
            Route(
                "/favicon.ico",
                endpoint=self._handle_favicon,
                methods=["GET"],
            )
        )

        return routes

    async def _handle_favicon(self, request: Request) -> Response:
        data = (
            Path(__file__).parent.parent / "res" / "favicon.ico"
        ).read_bytes()
        return Response(content=data, media_type="image/x-icon")

    async def _handle_login_page(self, request: Request) -> Response:
        """Serve the HTML login form."""
        flow_id = request.query_params.get("flow_id", "")

        if flow_id not in self._pending_flows:
            return HTMLResponse(
                content=render_error_page(
                    "Invalid or expired login link. "
                    "Please restart the connection from your MCP client."
                ),
                status_code=400,
            )

        return HTMLResponse(content=render_login_page(flow_id), status_code=200)

    async def _handle_login_submit(self, request: Request) -> Response:
        """Process login credentials via Kratos and redirect with code."""
        form = await request.form()
        flow_id = str(form.get("flow_id", ""))
        identifier = str(form.get("identifier", ""))
        password = str(form.get("password", ""))

        flow = self._pending_flows.get(flow_id)
        if not flow or flow["expires_at"] < _now():
            self._pending_flows.pop(flow_id, None)
            return HTMLResponse(
                content=render_error_page(
                    "Login session expired. "
                    "Please restart from your MCP client."
                ),
                status_code=400,
            )

        if not identifier or not password:
            return HTMLResponse(
                content=render_login_page(
                    flow_id,
                    error="Email and password are required.",
                ),
                status_code=400,
            )

        try:
            ory_token = await kratos_password_login(
                self.accounts_url, identifier, password
            )
            self._create_renewal_record(
                ory_token, StoredCredentials(identifier, password)
            )
            logger.info("Successful login for %s", identifier)
        except ValueError as e:
            logger.warning("Login failed for %s: %s", identifier, e)
            return HTMLResponse(
                content=render_login_page(
                    flow_id,
                    error="Invalid email or password.",
                ),
                status_code=401,
            )
        except Exception:
            logger.warning(
                "Login service error for %s", identifier, exc_info=True
            )
            return HTMLResponse(
                content=render_login_page(
                    flow_id,
                    error="Login service unavailable. Please try again.",
                ),
                status_code=502,
            )

        # Generate authorization code
        params: AuthorizationParams = flow["params"]
        client: OAuthClientInformationFull = flow["client"]

        code = secrets.token_urlsafe(32)
        self._auth_codes[code] = AuthorizationCode(
            code=code,
            scopes=params.scopes or [],
            expires_at=_now() + CODE_TTL,
            client_id=client.client_id or "",
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=(
                params.redirect_uri_provided_explicitly
            ),
        )
        self._code_tokens[code] = ory_token

        # Clean up the pending flow
        self._pending_flows.pop(flow_id, None)

        location = construct_redirect_uri(
            str(params.redirect_uri),
            code=code,
            state=params.state,
        )

        return Response(
            status_code=302,
            headers={"Location": location},
        )

    async def _get_session_ttl(self, token: str) -> int | None:
        """Get remaining TTL for a session token, or None if invalid."""
        async with httpx.AsyncClient(timeout=KRATOS_TIMEOUT) as client:
            resp = await client.get(
                f"{self.accounts_url}/auth/sessions/whoami",
                headers={"Authorization": f"Bearer {token}"},
            )

        if resp.status_code != 200:
            return None

        data = resp.json()
        try:
            expires_at = datetime.fromisoformat(data["expires_at"])
            remaining = int(expires_at.timestamp() - _now())
            return max(remaining, 0)
        except (KeyError, ValueError):
            return 3600  # Default 1 hour
