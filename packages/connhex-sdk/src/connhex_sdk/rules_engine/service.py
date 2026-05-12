from connhex_sdk.client import ConnhexClient
from connhex_sdk.rules_engine.schemas import (
    PagedRuleEvents,
    PagedRules,
    Rule,
    RuleSeverity,
    RuleStatus,
)


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
    ) -> PagedRules:
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
        return PagedRules.model_validate(resp.json())

    async def get_rule(self, rule_id: str, headers: dict) -> Rule:
        resp = await self.client.request("GET", f"/rules/{rule_id}", headers)
        return Rule.model_validate(resp.json())

    async def create_rule(self, data: dict, headers: dict) -> Rule:
        resp = await self.client.request(
            "POST",
            "/rules",
            headers,
            json=data,
            extra_headers={"Content-Type": "application/json"},
        )
        return Rule.model_validate(resp.json())

    async def update_rule(
        self, rule_id: str, data: dict, headers: dict
    ) -> Rule:
        resp = await self.client.request(
            "PATCH",
            f"/rules/{rule_id}",
            headers,
            json=data,
            extra_headers={"Content-Type": "application/json"},
        )
        return Rule.model_validate(resp.json())

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
    ) -> PagedRuleEvents:
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
        return PagedRuleEvents.model_validate(resp.json())
