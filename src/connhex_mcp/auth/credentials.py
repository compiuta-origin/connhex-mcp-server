import httpx
import asyncio
from dataclasses import dataclass, field


@dataclass
class CredentialsProvider:
    accounts_url: str
    username: str
    password: str
    _token: str | None = field(default=None, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)

    async def get_token(self) -> str:
        """Get cached token or perform login. Thread-safe."""
        if self._token:
            return self._token
        async with self._lock:
            if self._token:
                return self._token
            self._token = await self._login()
            return self._token

    async def refresh_token(self) -> str:
        """Force re-login (called on 401)."""
        async with self._lock:
            self._token = await self._login()
            return self._token

    async def _login(self) -> str:
        async with httpx.AsyncClient() as client:
            # Step 1: Create login flow
            flow_resp = await client.get(
                f"{self.accounts_url}/auth/self-service/login/api",
                headers={"Accept": "application/json"},
            )
            flow_resp.raise_for_status()
            action_url = flow_resp.json()["ui"]["action"]

            # Step 2: Submit credentials
            login_resp = await client.post(
                action_url,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                json={
                    "identifier": self.username,
                    "password": self.password,
                    "method": "password",
                },
            )
            login_resp.raise_for_status()
            token = login_resp.json()["session_token"]
            return token
