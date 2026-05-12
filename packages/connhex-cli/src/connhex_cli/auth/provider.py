from datetime import datetime, timedelta, timezone

import typer

from connhex_cli.auth import store


_EXPIRY_SKEW = timedelta(seconds=60)


def get_token(override_token: str | None = None) -> str:
    if override_token:
        return override_token

    creds = store.load()
    if creds is None:
        typer.echo("Not authenticated. Run `connhex login`.", err=True)
        raise typer.Exit(1)

    try:
        expires_at = datetime.fromisoformat(creds.expires_at)
    except ValueError:
        expires_at = None

    if expires_at is not None:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) + _EXPIRY_SKEW >= expires_at:
            typer.echo("Session expired. Run `connhex login`.", err=True)
            raise typer.Exit(1)

    return creds.token


def get_instance_url(override_url: str | None = None) -> str | None:
    if override_url:
        return override_url
    creds = store.load()
    return creds.instance_url if creds else None
