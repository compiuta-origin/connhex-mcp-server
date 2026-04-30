import asyncio
import logging
import secrets
import time
from datetime import datetime
from pathlib import Path

import httpx
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

from connhex_mcp.auth.kratos import KRATOS_TIMEOUT, kratos_password_login
from connhex_mcp.auth.templates import render_error_page, render_login_page
from connhex_mcp.config import Settings

logger = logging.getLogger("connhex-mcp")

FLOW_TTL = 300
CODE_TTL = 300


def _now() -> float:
    return time.time()


class ConnhexOAuthProvider(OAuthProvider):
    """OAuth provider that authenticates users via Connhex.

    Implements the full OAuth 2.0 authorization code flow with PKCE.
    """

    def __init__(self, settings: Settings):
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

        # Start background cleanup task
        self._cleanup_task: asyncio.Task | None = None

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
                now = _now()

                expired_flows = [
                    k
                    for k, v in self._pending_flows.items()
                    if v.get("expires_at", 0) < now
                ]
                for k in expired_flows:
                    self._pending_flows.pop(k, None)

                expired_codes = [
                    k
                    for k, v in self._auth_codes.items()
                    if (v.expires_at or 0) < now
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

            except Exception:
                logger.warning("Error in auth cleanup loop", exc_info=True)

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

        logger.info("Token exchange complete for client %s", client.client_id)
        return OAuthToken(
            access_token=ory_token,
            token_type="Bearer",
            expires_in=expires_in,
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        """Verify token via Kratos whoami endpoint."""
        # Check cache first
        cached = self._access_tokens.get(token)
        if cached and cached.expires_at and cached.expires_at > _now():
            logger.debug("Access token cache hit")
            return cached

        # Verify with Kratos
        async with httpx.AsyncClient(timeout=KRATOS_TIMEOUT) as client:
            resp = await client.get(
                f"{self.accounts_url}/auth/sessions/whoami",
                headers={"Authorization": f"Bearer {token}"},
            )

        if resp.status_code != 200:
            logger.warning(
                "Access token validation failed (status %s)", resp.status_code
            )
            self._access_tokens.pop(token, None)
            return None

        data = resp.json()
        try:
            expires_at = int(
                datetime.fromisoformat(data["expires_at"]).timestamp()
            )
        except (KeyError, ValueError):
            expires_at = int(_now() + 3600)

        access_token = AccessToken(
            token=token,
            client_id="",
            scopes=[],
            expires_at=expires_at,
        )
        self._access_tokens[token] = access_token
        return access_token

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
        """Remove token from local cache. Session remains valid in Kratos."""
        token_str = token.token if hasattr(token, "token") else str(token)
        self._access_tokens.pop(token_str, None)

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
