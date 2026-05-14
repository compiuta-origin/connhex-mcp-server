import asyncio
from dataclasses import dataclass, field

from connhex.auth.kratos import kratos_password_login


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
        return await kratos_password_login(
            self.accounts_url, self.username, self.password
        )
