import asyncio
from datetime import datetime, timedelta, timezone

import typer

from connhex_cli.auth import store
from connhex_cli.auth.models import StoredCreds
from connhex_cli.context import CLIContext
from connhex_cli.dependencies import get_iam_service
from connhex_cli.output import render

auth_app = typer.Typer(help="Authentication commands.")


@auth_app.command()
def login(
    ctx: typer.Context,
    instance_url: str = typer.Option(..., prompt="Instance URL"),
    username: str = typer.Option(..., prompt="Username"),
    password: str = typer.Option(
        ..., prompt=True, hide_input=True, confirmation_prompt=False
    ),
) -> None:
    """Log in and cache a session token."""
    from connhex_sdk.auth.kratos import kratos_password_login
    from connhex_sdk.config import CoreSettings

    settings = CoreSettings(
        instance_url=instance_url,
        auth_type="credentials",
        username=username,
        password=password,
    )  # type: ignore[call-arg]
    accounts_url = settings.accounts_url

    async def _login() -> str:
        return await kratos_password_login(accounts_url, username, password)

    try:
        token = asyncio.run(_login())
    except ValueError as e:
        typer.echo(f"Login failed: {e}", err=True)
        raise typer.Exit(1)

    async def _whoami(tok: str) -> dict:
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{accounts_url}/auth/sessions/whoami",
                headers={"Authorization": f"Bearer {tok}"},
            )
            resp.raise_for_status()
            return resp.json()

    try:
        session = asyncio.run(_whoami(token))
        expires_at_raw = session.get("expires_at")
        if expires_at_raw:
            expires_at = expires_at_raw
        else:
            expires_at = (
                datetime.now(timezone.utc) + timedelta(hours=24)
            ).isoformat()
    except Exception:
        expires_at = (
            datetime.now(timezone.utc) + timedelta(hours=24)
        ).isoformat()

    creds = StoredCreds(
        instance_url=instance_url,
        user=username,
        token=token,
        expires_at=expires_at,
    )
    path = store.save(creds)
    typer.echo(f"Logged in as {username}. Credentials saved to {path}.")
    typer.echo(f"Session expires at: {expires_at}")


@auth_app.command()
def logout(ctx: typer.Context) -> None:
    """Clear cached credentials."""
    if store.clear():
        typer.echo("Logged out.")
    else:
        typer.echo("Already logged out.")


@auth_app.command()
def whoami(ctx: typer.Context) -> None:
    """Show current user info (hits the network)."""
    cli_ctx: CLIContext = ctx.obj
    svc = get_iam_service(ctx)

    async def _run() -> dict:
        return await svc.whoami({})

    result = asyncio.run(_run())
    render(result, cli_ctx.output)


@auth_app.command()
def status(ctx: typer.Context) -> None:
    """Show local credential status without hitting the network."""
    creds = store.load()
    if creds is None:
        typer.echo("Not authenticated.")
        return

    try:
        expires_at = datetime.fromisoformat(creds.expires_at)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = expires_at - now
        if delta.total_seconds() <= 0:
            time_left = "EXPIRED"
        else:
            hours, rem = divmod(int(delta.total_seconds()), 3600)
            minutes = rem // 60
            time_left = f"{hours}h {minutes}m"
    except ValueError:
        time_left = "unknown"

    masked = creds.token[:12] + "..." if len(creds.token) > 12 else "***"
    typer.echo(f"User:        {creds.user}")
    typer.echo(f"Instance:    {creds.instance_url}")
    typer.echo(f"Token:       {masked}")
    typer.echo(f"Expires at:  {creds.expires_at}")
    typer.echo(f"Time left:   {time_left}")
