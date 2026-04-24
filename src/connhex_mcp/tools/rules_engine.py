from typing import Annotated

from fastmcp.server.dependencies import get_http_headers

from connhex_mcp.dependencies import get_rules_engine_service
from connhex_mcp.mcp_instance import mcp
from connhex_mcp.services.rules_engine import (
    Condition,
    Notification,
    PagedRuleEvents,
    PagedRules,
    Processable,
    Rule,
    RuleSeverity,
    RuleSort,
    RuleStatus,
    Tag,
)


def _dump(model) -> dict:
    return model.model_dump(by_alias=True, exclude_none=True)


@mcp.tool()
async def list_rules(
    ids: Annotated[list[str] | None, "Filter by specific rule IDs."] = None,
    tag_labels: Annotated[list[str] | None, "Filter by tag labels."] = None,
    tag_label_values: Annotated[
        list[str] | None, "Filter by tag label values."
    ] = None,
    severity: Annotated[RuleSeverity | None, "Filter by severity."] = None,
    status: Annotated[RuleStatus | None, "Filter by status."] = None,
    page: Annotated[int, "Page number (0-indexed)."] = 0,
    page_size: Annotated[int, "Results per page (default 1000)."] = 1000,
    sort: RuleSort = "createdAt:desc",
) -> PagedRules:
    """List rules from the Connhex Rules Engine."""
    headers = get_http_headers() or {}
    data = await get_rules_engine_service().list_rules(
        headers,
        ids=ids,
        tag_labels=tag_labels,
        tag_label_values=tag_label_values,
        severity=severity,
        status=status,
        page=page,
        page_size=page_size,
        sort=sort,
    )
    return PagedRules.model_validate(data)


@mcp.tool()
async def get_rule(rule_id: Annotated[str, "Rule ID."]) -> Rule:
    """Get a single rule by ID from the Connhex Rules Engine."""
    headers = get_http_headers() or {}
    data = await get_rules_engine_service().get_rule(rule_id, headers)
    return Rule.model_validate(data)


@mcp.tool()
async def create_rule(
    name: Annotated[str, "Human-readable rule name."],
    notification: Notification,
    conditions: Annotated[
        list[Condition],
        "All conditions must hold for the rule to trigger.",
    ],
    severity: RuleSeverity | None = None,
    description: Annotated[str | None, "Optional description."] = None,
    processable: Annotated[
        Processable | None,
        'Whether the rule is processed (default "enabled").',
    ] = None,
    tags: list[Tag] | None = None,
) -> Rule:
    """Create a new rule in the Connhex Rules Engine."""
    headers = get_http_headers() or {}
    payload: dict = {
        "name": name,
        "notification": _dump(notification),
        "conditions": [_dump(c) for c in conditions],
    }
    if severity is not None:
        payload["severity"] = severity
    if description is not None:
        payload["description"] = description
    if processable is not None:
        payload["processable"] = processable
    if tags is not None:
        payload["tags"] = [_dump(t) for t in tags]

    data = await get_rules_engine_service().create_rule(payload, headers)
    return Rule.model_validate(data)


@mcp.tool()
async def update_rule(
    rule_id: Annotated[str, "Rule ID."],
    name: Annotated[str | None, "New name."] = None,
    notification: Notification | None = None,
    conditions: Annotated[
        list[Condition] | None,
        "Replace the rule's conditions.",
    ] = None,
    severity: RuleSeverity | None = None,
    description: Annotated[str | None, "New description."] = None,
    processable: Processable | None = None,
    tags: list[Tag] | None = None,
) -> Rule:
    """Partially update a rule. Only the fields provided are changed."""
    headers = get_http_headers() or {}
    payload: dict = {}
    if name is not None:
        payload["name"] = name
    if notification is not None:
        payload["notification"] = _dump(notification)
    if conditions is not None:
        payload["conditions"] = [_dump(c) for c in conditions]
    if severity is not None:
        payload["severity"] = severity
    if description is not None:
        payload["description"] = description
    if processable is not None:
        payload["processable"] = processable
    if tags is not None:
        payload["tags"] = [_dump(t) for t in tags]

    data = await get_rules_engine_service().update_rule(
        rule_id, payload, headers
    )
    return Rule.model_validate(data)


@mcp.tool()
async def delete_rule(
    rule_id: Annotated[str, "Rule ID."],
) -> str:
    """Delete a rule. This action is irreversible."""
    headers = get_http_headers() or {}
    await get_rules_engine_service().delete_rule(rule_id, headers)
    return f"Rule {rule_id} deleted successfully."


@mcp.tool()
async def list_rule_events(
    rule_ids: Annotated[list[str] | None, "Filter by rule IDs."] = None,
    from_date: Annotated[
        str | None, "ISO-8601 date-time lower bound (inclusive)."
    ] = None,
    to_date: Annotated[
        str | None, "ISO-8601 date-time upper bound (inclusive)."
    ] = None,
    status: Annotated[RuleStatus | None, "Filter by event status."] = None,
    page: Annotated[int, "Page number (0-indexed)."] = 0,
    page_size: Annotated[int, "Results per page (default 1000)."] = 1000,
    sort: RuleSort = "createdAt:desc",
) -> PagedRuleEvents:
    """List rule events (triggered rule occurrences)."""
    headers = get_http_headers() or {}
    data = await get_rules_engine_service().list_rule_events(
        headers,
        rule_ids=rule_ids,
        from_date=from_date,
        to_date=to_date,
        status=status,
        page=page,
        page_size=page_size,
        sort=sort,
    )
    return PagedRuleEvents.model_validate(data)
