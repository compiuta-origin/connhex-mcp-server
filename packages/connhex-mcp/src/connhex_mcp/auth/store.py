import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Protocol

from mcp.shared.auth import OAuthClientInformationFull
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class OAuthClientStore(Protocol):
    def get(self, client_id: str) -> OAuthClientInformationFull | None: ...

    def put(self, client_info: OAuthClientInformationFull) -> None: ...


class InMemoryOAuthClientStore:
    def __init__(self) -> None:
        self._clients: dict[str, OAuthClientInformationFull] = {}

    def get(self, client_id: str) -> OAuthClientInformationFull | None:
        return self._clients.get(client_id)

    def put(self, client_info: OAuthClientInformationFull) -> None:
        if client_info.client_id:
            self._clients[client_info.client_id] = client_info


class SQLiteOAuthClientStore:
    """Persists dynamic OAuth client registrations across pod restarts."""

    def __init__(self, path: str):
        self.path = Path(path)
        parent = self.path.parent
        if not parent.exists():
            raise ValueError(
                f"OAuth client store directory does not exist: {parent}"
            )
        if not parent.is_dir():
            raise ValueError(
                f"OAuth client store parent is not a directory: {parent}"
            )

        try:
            self._ensure_schema()
        except sqlite3.Error as exc:
            raise ValueError(
                "Unable to initialize OAuth client SQLite store at "
                f"{self.path}: {exc}"
            ) from exc

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS oauth_clients (
                    client_id TEXT PRIMARY KEY,
                    client_info TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
                """
            )

    def get(self, client_id: str) -> OAuthClientInformationFull | None:
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT client_info FROM oauth_clients WHERE client_id = ?",
                    (client_id,),
                ).fetchone()
        except sqlite3.Error:
            logger.warning(
                "Failed to load OAuth client %s from SQLite store",
                client_id,
                exc_info=True,
            )
            return None

        if row is None:
            return None

        try:
            return OAuthClientInformationFull.model_validate(json.loads(row[0]))
        except (json.JSONDecodeError, TypeError, ValidationError):
            logger.warning(
                "Ignoring invalid persisted OAuth client %s",
                client_id,
                exc_info=True,
            )
            return None

    def put(self, client_info: OAuthClientInformationFull) -> None:
        if not client_info.client_id:
            return

        now = int(time.time())
        payload = json.dumps(
            client_info.model_dump(mode="json"),
            sort_keys=True,
        )

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO oauth_clients (
                    client_id,
                    client_info,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?)
                ON CONFLICT(client_id) DO UPDATE SET
                    client_info = excluded.client_info,
                    updated_at = excluded.updated_at
                """,
                (client_info.client_id, payload, now, now),
            )
