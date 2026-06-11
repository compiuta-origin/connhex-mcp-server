import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import typer
from connhex.errors import ConnhexAPIError
from connhex.schemas.provision import BulkResult, ProvisionedThing
from connhex_cli.commands.connectables import register

FIXTURE = Path(__file__).parent / "fixtures" / "test_provision.csv"


class FakeProvisionSvc:
    def __init__(self, bulk: BulkResult):
        self._bulk = bulk
        self.provisioned: list = []
        self.unprovisioned: list[str] | None = None

    def bulk_provision(self, items):
        self.provisioned = list(items)
        return self._bulk

    def bulk_unprovision(self, ids):
        self.unprovisioned = list(ids)


class FakeManufacturingSvc:
    def __init__(self, schema: dict[str, Any], fail_on: int | None = None):
        self.schema = schema
        self.fail_on = fail_on
        self.creates: list[dict] = []

    def get_schema(self) -> dict:
        return self.schema

    def create(self, resource_type: str, data: dict):
        if self.fail_on is not None and len(self.creates) == self.fail_on:
            raise ConnhexAPIError(
                status=500,
                detail="boom",
                response=httpx.Response(
                    500,
                    request=httpx.Request(
                        "POST",
                        f"https://connhex.test/{resource_type}",
                    ),
                ),
            )
        self.creates.append({"type": resource_type, "data": data})
        return {"ok": True}


SCHEMA = {
    "devices": {
        "deviceType": {"type": "String"},
        "serialNumber": {"type": "String"},
        "connhexId": {"type": "String"},
        "name": {"type": "String"},
    }
}


def _bulk(n: int) -> BulkResult:
    things = [
        ProvisionedThing(id=f"id-{i}", name=f"n{i}", key=f"k{i}")
        for i in range(n)
    ]
    return BulkResult(things=things, processed=n, failed=0, errors=[])


def test_happy_path_csv() -> None:
    prov = FakeProvisionSvc(_bulk(4))
    mfg = FakeManufacturingSvc(SCHEMA)
    result = register.run(
        str(FIXTURE),
        None,
        schema="devices",
        serial_field="serialNumber",
        connhex_field="connhexId",
        provision_svc=prov,
        manufacturing_svc=mfg,
    )
    assert result["registered"] == 4
    assert len(prov.provisioned) == 4
    assert len(mfg.creates) == 4
    first = mfg.creates[0]["data"]["data"]
    assert first["type"] == "devices"
    assert first["attributes"]["serialNumber"] == "SN123456789"
    assert first["attributes"]["connhexId"] == "id-0"
    assert first["attributes"]["deviceType"] == "raspberrypi"
    assert prov.unprovisioned is None


def test_rollback_on_manufacturing_failure() -> None:
    prov = FakeProvisionSvc(_bulk(4))
    mfg = FakeManufacturingSvc(SCHEMA, fail_on=2)
    with pytest.raises(typer.BadParameter, match="rolled back"):
        register.run(
            str(FIXTURE),
            None,
            schema="devices",
            serial_field="serialNumber",
            connhex_field="connhexId",
            provision_svc=prov,
            manufacturing_svc=mfg,
        )
    assert prov.unprovisioned == ["id-0", "id-1", "id-2", "id-3"]


def test_unknown_schema_type_fails_with_hint() -> None:
    prov = FakeProvisionSvc(_bulk(4))
    mfg = FakeManufacturingSvc(SCHEMA)
    with pytest.raises(typer.BadParameter, match="Available: devices"):
        register.run(
            str(FIXTURE),
            None,
            schema="device",  # schema doc has "devices"
            serial_field="serialNumber",
            connhex_field="connhexId",
            provision_svc=prov,
            manufacturing_svc=mfg,
        )
    assert prov.provisioned == []  # no API call before schema check


def test_tenant_emitted_as_attribute(tmp_path: Path) -> None:
    src = tmp_path / "x.json"
    src.write_text(
        json.dumps(
            [
                {
                    "provision": {"init_id": "SN1", "init_key": "k1"},
                    "manufacturing": {"device_type": "rpi"},
                    "tenant": "tenant-a",
                }
            ]
        )
    )
    prov = FakeProvisionSvc(_bulk(1))
    mfg = FakeManufacturingSvc(SCHEMA)
    register.run(
        str(src),
        None,
        schema="devices",
        serial_field="serialNumber",
        connhex_field="connhexId",
        provision_svc=prov,
        manufacturing_svc=mfg,
    )
    payload = mfg.creates[0]["data"]["data"]
    assert payload["attributes"]["tenants"] == ["tenant-a"]
    assert "relationships" not in payload
