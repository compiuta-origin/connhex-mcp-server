import json

import typer
from connhex.schemas.rules_engine import RuleSeverity, RuleStatus

from connhex_cli.client import connhex_client
from connhex_cli.context import CLIContext
from connhex_cli.output import render

rules_app = typer.Typer(help="Manage rules engine rules.")


@rules_app.command("list")
def list_rules(
    ctx: typer.Context,
    ids: list[str] | None = typer.Option(
        None, "--id", help="Filter by rule ID. Repeat for multiple."
    ),
    tag_labels: list[str] | None = typer.Option(
        None, "--tag-label", help="Filter by tag label. Repeat for multiple."
    ),
    tag_label_values: list[str] | None = typer.Option(
        None,
        "--tag-label-value",
        help="Filter by tag label value. Repeat for multiple.",
    ),
    severity: RuleSeverity | None = typer.Option(
        None, help="Filter by severity."
    ),
    status: RuleStatus | None = typer.Option(None, help="Filter by status."),
    page: int = typer.Option(0, help="Page number (0-indexed)."),
    page_size: int = typer.Option(1000, help="Results per page."),
    sort: str = typer.Option("createdAt:desc", help="Sort expression."),
) -> None:
    """List rules."""
    cli_ctx: CLIContext = ctx.obj
    c = connhex_client(ctx)
    result = c.rules.list_rules(
        ids=ids,
        tag_labels=tag_labels,
        tag_label_values=tag_label_values,
        severity=severity,
        status=status,
        page=page,
        page_size=page_size,
        sort=sort,
    )
    render(result.results, cli_ctx.output)


@rules_app.command("get")
def get_rule(ctx: typer.Context, rule_id: str = typer.Argument(...)) -> None:
    """Get a rule by ID."""
    cli_ctx: CLIContext = ctx.obj
    c = connhex_client(ctx)
    render(c.rules.get_rule(rule_id), cli_ctx.output)


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
    c = connhex_client(ctx)
    render(c.rules.create_rule(data), cli_ctx.output)


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
    c = connhex_client(ctx)
    render(c.rules.update_rule(rule_id, data), cli_ctx.output)


@rules_app.command("delete")
def delete_rule(ctx: typer.Context, rule_id: str = typer.Argument(...)) -> None:
    """Delete a rule."""
    c = connhex_client(ctx)
    c.rules.delete_rule(rule_id)
    typer.echo(f"Rule {rule_id} deleted.")


@rules_app.command("events")
def list_events(
    ctx: typer.Context,
    rule_ids: list[str] | None = typer.Option(
        None, "--rule-id", help="Filter by rule ID. Repeat for multiple."
    ),
    from_date: str | None = typer.Option(None, "--from"),
    to_date: str | None = typer.Option(None, "--to"),
    status: RuleStatus | None = typer.Option(None, help="Filter by status."),
    page: int = typer.Option(0),
    page_size: int = typer.Option(1000),
    sort: str = typer.Option("createdAt:desc", help="Sort expression."),
) -> None:
    """List rule events."""
    cli_ctx: CLIContext = ctx.obj
    c = connhex_client(ctx)
    result = c.rules.list_rule_events(
        rule_ids=rule_ids,
        from_date=from_date,
        to_date=to_date,
        status=status,
        page=page,
        page_size=page_size,
        sort=sort,
    )
    render(result.results, cli_ctx.output)
