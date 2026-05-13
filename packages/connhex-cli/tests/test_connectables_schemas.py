from __future__ import annotations

import pytest
from pydantic import ValidationError

from connhex_cli.commands.connectables.schemas import (
    Connectable,
    ConnectablesBatch,
)

SCHEMA_ATTRS = {"deviceType", "serialNumber", "connhexId"}
CONTEXT = {
    "schema_attrs": SCHEMA_ATTRS,
    "serial_field": "serialNumber",
    "connhex_field": "connhexId",
}


def _make(rows: list[dict]) -> ConnectablesBatch:
    return ConnectablesBatch.model_validate({"items": rows}, context=CONTEXT)


def test_snake_case_keys_normalized_to_camel() -> None:
    batch = _make(
        [
            {
                "provision": {"init_id": "SN1"},
                "manufacturing": {"device_type": "rpi"},
                "row": 2,
            }
        ]
    )
    assert batch.items[0].manufacturing == {"deviceType": "rpi"}


def test_unknown_manufacturing_field_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown manufacturing"):
        _make(
            [
                {
                    "provision": {"init_id": "SN1"},
                    "manufacturing": {"bogusField": "x"},
                    "row": 2,
                }
            ]
        )


def test_serial_field_forbidden_in_input() -> None:
    with pytest.raises(ValidationError, match="must not be set in input"):
        _make(
            [
                {
                    "provision": {"init_id": "SN1"},
                    "manufacturing": {"serialNumber": "X"},
                    "row": 2,
                }
            ]
        )


def test_duplicate_init_id() -> None:
    with pytest.raises(ValidationError, match="duplicate init_id"):
        _make(
            [
                {
                    "provision": {
                        "init_id": "SN1",
                        "init_key": "5fce8d40-2bc4-44b5-9094-46e63de1d3b9",
                    },
                    "row": 2,
                },
                {
                    "provision": {
                        "init_id": "SN1",
                        "init_key": "5fce8d40-2bc4-44b5-9094-46e63de1d3ba",
                    },
                    "row": 3,
                },
            ]
        )


def test_duplicate_init_key() -> None:
    with pytest.raises(ValidationError, match="duplicate init_key"):
        _make(
            [
                {
                    "provision": {"init_id": "SN1", "init_key": "K"},
                    "row": 2,
                },
                {
                    "provision": {"init_id": "SN2", "init_key": "K"},
                    "row": 3,
                },
            ]
        )


def test_serial_or_connhex_field_missing_from_schema() -> None:
    with pytest.raises(ValidationError, match="not in the manufacturing"):
        ConnectablesBatch.model_validate(
            {
                "items": [
                    {
                        "provision": {"init_id": "SN1"},
                        "manufacturing": {},
                        "row": 2,
                    }
                ]
            },
            context={
                "schema_attrs": SCHEMA_ATTRS,
                "serial_field": "missing_field",
                "connhex_field": "connhexId",
            },
        )


def test_happy_path() -> None:
    batch = _make(
        [
            {
                "provision": {
                    "init_id": "SN1",
                    "init_key": "k1",
                },
                "manufacturing": {"device_type": "rpi"},
                "tenant": "tenant-a",
                "row": 2,
            },
            {
                "provision": {
                    "init_id": "SN2",
                    "init_key": "k2",
                },
                "manufacturing": {"deviceType": "rpi"},
                "row": 3,
            },
        ]
    )
    assert len(batch.items) == 2
    assert batch.items[0].tenant == "tenant-a"
    assert batch.items[1].provision.init_id == "SN2"


def test_no_schema_skips_field_check() -> None:
    # When schema_attrs is None, unknown fields are allowed.
    batch = ConnectablesBatch.model_validate(
        {
            "items": [
                {
                    "provision": {"init_id": "SN1"},
                    "manufacturing": {"anyField": "x"},
                    "row": 2,
                }
            ]
        },
        context={
            "schema_attrs": None,
            "serial_field": "serialNumber",
            "connhex_field": "connhexId",
        },
    )
    assert batch.items[0].manufacturing == {"anyField": "x"}


def test_connectable_construction_validates_init_id() -> None:
    with pytest.raises(ValidationError):
        Connectable.model_validate(
            {"provision": {"init_id": ""}}, context=CONTEXT
        )
