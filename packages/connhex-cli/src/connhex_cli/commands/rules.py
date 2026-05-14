import json

import typer

from connhex_cli.client import run
from connhex_cli.context import CLIContext
from connhex_cli.output import render

rules_app = typer.Typer(help="Manage rules engine rules.")


@rules_app.command("list")
def list_rules(
    ctx: typer.Context,
    severity: str | None = typer.Option(None, help="Filter by severity."),
    status: str | None = typer.Option(None, help="Filter by status."),
    page: int = typer.Option(0, help="Page number (0-indexed)."),
    page_size: int = typer.Option(1000, help="Results per page."),
) -> None:
    """List rules."""
    cli_ctx: CLIContext = ctx.obj
    result = run(
        ctx,
        lambda c: c.rules.list_rules(
            severity=severity,
            status=status,
            page=page,
            page_size=page_size,
        ),
    )
    render(result.results, cli_ctx.output)


@rules_app.command("get")
def get_rule(ctx: typer.Context, rule_id: str = typer.Argument(...)) -> None:
    """Get a rule by ID."""
    cli_ctx: CLIContext = ctx.obj
    render(run(ctx, lambda c: c.rules.get_rule(rule_id)), cli_ctx.output)


@rules_app.command("create")
def create_rule(
    ctx: typer.Context,
    payload: str = typer.Argument(..., help="Full rule JSON payload."),
) -> None:
    """Create a rule from a JSON payload."""
    cli_ctx: CLIContext = ctx.obj
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        typer.echo(f"Invalid JSON: {e}", err=True)
        raise typer.Exit(1)
    render(run(ctx, lambda c: c.rules.create_rule(data)), cli_ctx.output)


@rules_app.command("update")
def update_rule(
    ctx: typer.Context,
    rule_id: str = typer.Argument(...),
    payload: str = typer.Argument(..., help="Partial rule JSON payload."),
) -> None:
    """Update a rule."""
    cli_ctx: CLIContext = ctx.obj
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        typer.echo(f"Invalid JSON: {e}", err=True)
        raise typer.Exit(1)
    render(
        run(ctx, lambda c: c.rules.update_rule(rule_id, data)),
        cli_ctx.output,
    )


@rules_app.command("delete")
def delete_rule(ctx: typer.Context, rule_id: str = typer.Argument(...)) -> None:
    """Delete a rule."""
    run(ctx, lambda c: c.rules.delete_rule(rule_id))
    typer.echo(f"Rule {rule_id} deleted.")


@rules_app.command("events")
def list_events(
    ctx: typer.Context,
    rule_id: str | None = typer.Argument(None, help="Filter by rule ID."),
    from_date: str | None = typer.Option(None, "--from"),
    to_date: str | None = typer.Option(None, "--to"),
    page: int = typer.Option(0),
    page_size: int = typer.Option(1000),
) -> None:
    """List rule events."""
    cli_ctx: CLIContext = ctx.obj
    rule_ids = [rule_id] if rule_id else None
    result = run(
        ctx,
        lambda c: c.rules.list_rule_events(
            rule_ids=rule_ids,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        ),
    )
    render(result.results, cli_ctx.output)
