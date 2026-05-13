from typing import Any

from connhex_sdk.provision import ProvisionData
from connhex_sdk.schemas import ConnhexBaseModel
from pydantic import Field, ValidationInfo, model_validator

from connhex_cli.commands.connectables.casing import snake_to_camel


class Connectable(ConnhexBaseModel):
    """A device to register: provision data + manufacturing attributes."""

    provision: ProvisionData
    manufacturing: dict[str, Any] = Field(default_factory=dict)
    tenant: str | None = None
    row: int | None = Field(default=None, exclude=True)

    @model_validator(mode="before")
    @classmethod
    def _normalize_manufacturing_keys(cls, data: object) -> object:
        if isinstance(data, dict):
            mfg = data.get("manufacturing")
            if isinstance(mfg, dict):
                normalized = {snake_to_camel(k): v for k, v in mfg.items()}
                data = {**data, "manufacturing": normalized}
        return data

    @model_validator(mode="after")
    def _validate_manufacturing(self, info: ValidationInfo) -> "Connectable":
        ctx = info.context or {}
        serial_field = ctx.get("serial_field")
        connhex_field = ctx.get("connhex_field")
        schema_attrs: set[str] | None = ctx.get("schema_attrs")

        where = f" (row {self.row})" if self.row is not None else ""

        if serial_field and serial_field in self.manufacturing:
            raise ValueError(
                f"manufacturing.{serial_field} must not be set in input"
                f"{where}; it is auto-filled from provision.init_id"
            )

        if schema_attrs is not None:
            unknown = [k for k in self.manufacturing if k not in schema_attrs]
            if unknown:
                raise ValueError(
                    f"unknown manufacturing fields{where}: "
                    f"{', '.join(sorted(unknown))}. "
                    f"Allowed: {', '.join(sorted(schema_attrs))}"
                )
            for required in (serial_field, connhex_field):
                if required and required not in schema_attrs:
                    raise ValueError(
                        f"field '{required}' is not in the manufacturing "
                        f"schema; cannot be auto-filled"
                    )

        return self


class ConnectablesBatch(ConnhexBaseModel):
    items: list[Connectable]

    @model_validator(mode="after")
    def _no_duplicates(self) -> "ConnectablesBatch":
        seen_id: dict[str, list[int]] = {}
        seen_key: dict[str, list[int]] = {}
        for c in self.items:
            row = c.row if c.row is not None else -1
            seen_id.setdefault(c.provision.init_id, []).append(row)
            seen_key.setdefault(c.provision.init_key, []).append(row)

        dupe_msgs = []
        for init_id, rows in seen_id.items():
            if len(rows) > 1:
                dupe_msgs.append(
                    f"duplicate init_id '{init_id}' in rows {rows}"
                )
        for init_key, rows in seen_key.items():
            if len(rows) > 1:
                dupe_msgs.append(
                    f"duplicate init_key '{init_key}' in rows {rows}"
                )
        if dupe_msgs:
            raise ValueError("; ".join(dupe_msgs))
        return self
