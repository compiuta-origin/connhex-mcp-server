from datetime import datetime, timedelta, timezone

import httpx
import typer
from connhex.sync.auth import password_login
from connhex.urls import DEFAULT_INSTANCE_URL, build_accounts_url

from connhex_cli.auth import store
from connhex_cli.auth.models import StoredCreds
from connhex_cli.client import connhex_client
from connhex_cli.context import CLIContext
from connhex_cli.output import render

auth_app = typer.Typer(help="Authentication commands.")


@auth_app.command()
def login(
    ctx: typer.Context,
    instance_url: str = typer.Option(
        DEFAULT_INSTANCE_URL, prompt="Instance URL"
    ),
    username: str = typer.Option(..., prompt="Username"),
    password: str = typer.Option(
        ..., prompt=True, hide_input=True, confirmation_prompt=False
    ),
) -> None:
    """Log in and cache a session token."""
    try:
        token = password_login(instance_url, username, password)
    except ValueError as e:
        typer.echo(f"Login failed: {e}", err=True)
        raise typer.Exit(1)

    accounts_url = build_accounts_url(instance_url)
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{accounts_url}/auth/sessions/whoami",
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            session = resp.json()
        expires_at = (
            session.get("expires_at")
            or (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
        )
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
    c = connhex_client(ctx)
    render(c.iam.whoami(), cli_ctx.output)


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
