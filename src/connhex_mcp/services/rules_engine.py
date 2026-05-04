from typing import Annotated, Literal

from pydantic import Field

from connhex_mcp.client import ConnhexClient
from connhex_mcp.utils.schemas import ConnhexBaseModel

RuleSeverity = Literal["info", "warning", "critical"]
RuleStatus = Literal["active", "inactive"]
MessageSource = Literal["messages", "params", "metrics"]
ComparisonOperator = Literal[">", ">=", "<", "<=", "==", "!="]
NotificationPolicy = Literal["trigger", "reentry"]
NotificationMedium = Literal[
    "email", "telegram", "sms", "slack", "discord", "fcm", "msteams"
]
Processable = Literal["enabled", "disabled"]
RuleSort = Literal[
    "createdAt:asc", "createdAt:desc", "status:asc", "status:desc"
]


class ActiveWindow(ConnhexBaseModel):
    from_: str = Field(alias="from", description='HH:MM, e.g. "08:10".')
    to: str = Field(description='HH:MM, e.g. "13:15".')
    timezone: str = Field(description='IANA timezone, e.g. "Europe/Rome".')

    model_config = {"populate_by_name": True}


class ThresholdConditionParams(ConnhexBaseModel):
    metric: str = Field(description="Metric URN.")
    threshold: float
    comparisonOperator: ComparisonOperator
    durationSecs: int = Field(ge=0, le=86400)
    channelId: str
    source: MessageSource | None = None
    unit: str | None = None
    activeWindow: ActiveWindow | None = None


class LastMessageOlderThanConditionParams(ConnhexBaseModel):
    channelId: str
    durationSecs: int = Field(ge=0, le=86400)
    source: MessageSource | None = None
    metric: str | None = Field(
        default=None,
        description=(
            "If specified, the condition will be evaluated based on the "
            "metric value of the last message in the channel. The value "
            "may optionally end with a single wildcard (`*`) to match any "
            'suffix. No other wildcard placements are allowed (e.g. "cpu'
            '*idle", "*cpu", or multiple `*` are invalid).'
        ),
    )
    activeWindow: ActiveWindow | None = None


class DeltaConditionParams(ConnhexBaseModel):
    metric: str = Field(description="Metric URN.")
    delta: float
    channelId: str
    comparisonOperator: ComparisonOperator
    durationSecs: int = Field(ge=0, le=86400)
    source: MessageSource | None = None
    unit: str | None = None
    activeWindow: ActiveWindow | None = None


class ThresholdCondition(ConnhexBaseModel):
    type: Literal["threshold"]
    params: ThresholdConditionParams


class LastMessageOlderThanCondition(ConnhexBaseModel):
    type: Literal["lastMessageOlderThan"]
    params: LastMessageOlderThanConditionParams


class DeltaCondition(ConnhexBaseModel):
    type: Literal["delta"]
    params: DeltaConditionParams


Condition = Annotated[
    ThresholdCondition | LastMessageOlderThanCondition | DeltaCondition,
    Field(discriminator="type"),
]


class NotificationMessage(ConnhexBaseModel):
    policy: NotificationPolicy = Field(
        description=(
            "Defines when the notification should be dispatched:\n"
            "- `trigger`: the notification is sent when the rule is triggered "
            "(its conditions are satisfied).\n"
            "- `reentry`: The notification is sent when the rule re-enters "
            "(its associated conditions are no longer satisfied)"
        )
    )
    medium: NotificationMedium
    text: str
    target: str | None = Field(
        default=None,
        description=(
            "Recipient. Format depends on medium (email address, E.164 "
            "phone, webhook URL, device token, ...). If not specified, "
            "the notification is sent to the user who created the rule."
        ),
    )


class Notification(ConnhexBaseModel):
    messages: list[NotificationMessage]


class Tag(ConnhexBaseModel):
    label: str = Field(description='Tag key, e.g. "deviceID".')
    labelValue: str
    metadata: dict | None = None


class ReadConditionDto(ConnhexBaseModel):
    id: str
    type: Literal["threshold", "lastMessageOlderThan", "delta"]
    status: RuleStatus | None = None
    params: dict
    createdAt: str | None = None
    updatedAt: str | None = None
    deletedAt: str | None = None


class ReadTagDto(ConnhexBaseModel):
    id: str
    label: str
    labelValue: str
    metadata: dict | None = None
    createdAt: str | None = None
    updatedAt: str | None = None
    deletedAt: str | None = None


class Rule(ConnhexBaseModel):
    id: str
    name: str
    status: RuleStatus | None = None
    severity: RuleSeverity | None = None
    description: str | None = None
    processable: Processable | None = None
    conditions: list[ReadConditionDto]
    tags: list[ReadTagDto] = []
    notification: Notification
    createdAt: str | None = None
    updatedAt: str | None = None
    deletedAt: str | None = None


class PagedRules(ConnhexBaseModel):
    results: list[Rule]
    total: int


class ReadConditionEventDto(ConnhexBaseModel):
    id: str
    conditionId: str
    conditionSnapshot: dict
    status: RuleStatus | None = None
    createdAt: str | None = None


class RuleEvent(ConnhexBaseModel):
    id: str
    ruleId: str
    status: RuleStatus | None = None
    conditionsEvents: list[ReadConditionEventDto]
    createdAt: str | None = None


class PagedRuleEvents(ConnhexBaseModel):
    results: list[RuleEvent]
    total: int


class RulesEngineService:
    def __init__(self, client: ConnhexClient):
        self.client = client

    async def list_rules(
        self,
        headers: dict,
        *,
        ids: list[str] | None = None,
        tag_labels: list[str] | None = None,
        tag_label_values: list[str] | None = None,
        severity: RuleSeverity | None = None,
        status: RuleStatus | None = None,
        page: int = 0,
        page_size: int = 1000,
        sort: str = "createdAt:desc",
    ) -> dict:
        params: dict = {
            "page": page,
            "pageSize": page_size,
            "sort": sort,
        }
        if ids:
            params["ids"] = ids
        if tag_labels:
            params["tagLabels"] = tag_labels
        if tag_label_values:
            params["tagLabelValues"] = tag_label_values
        if severity is not None:
            params["severity"] = severity
        if status is not None:
            params["status"] = status

        resp = await self.client.request(
            "GET", "/rules", headers, params=params
        )
        return resp.json()

    async def get_rule(self, rule_id: str, headers: dict) -> dict:
        resp = await self.client.request("GET", f"/rules/{rule_id}", headers)
        return resp.json()

    async def create_rule(self, data: dict, headers: dict) -> dict:
        resp = await self.client.request(
            "POST",
            "/rules",
            headers,
            json=data,
            extra_headers={"Content-Type": "application/json"},
        )
        return resp.json()

    async def update_rule(
        self, rule_id: str, data: dict, headers: dict
    ) -> dict:
        resp = await self.client.request(
            "PATCH",
            f"/rules/{rule_id}",
            headers,
            json=data,
            extra_headers={"Content-Type": "application/json"},
        )
        return resp.json()

    async def delete_rule(self, rule_id: str, headers: dict) -> None:
        await self.client.request("DELETE", f"/rules/{rule_id}", headers)

    async def list_rule_events(
        self,
        headers: dict,
        *,
        rule_ids: list[str] | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        status: RuleStatus | None = None,
        page: int = 0,
        page_size: int = 1000,
        sort: str = "createdAt:desc",
    ) -> dict:
        params: dict = {
            "page": page,
            "pageSize": page_size,
            "sort": sort,
        }
        if rule_ids:
            params["ruleIds"] = rule_ids
        if from_date is not None:
            params["from"] = from_date
        if to_date is not None:
            params["to"] = to_date
        if status is not None:
            params["status"] = status

        resp = await self.client.request(
            "GET", "/rules/events", headers, params=params
        )
        return resp.json()
