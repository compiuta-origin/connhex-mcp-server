from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from connhex_cli.commands.connectables.loader import LoaderError, load

FIXTURE = Path(__file__).parent / "fixtures" / "test_provision.csv"


def test_load_csv_from_path() -> None:
    rows = load(str(FIXTURE))
    assert len(rows) == 4
    assert rows[0]["provision"]["init_id"] == "SN123456789"
    assert rows[0]["manufacturing"]["device_type"] == "raspberrypi"
    assert rows[0]["row"] == 2  # data rows start at line 2


def test_load_csv_skips_empty_cells(tmp_path: Path) -> None:
    p = tmp_path / "x.csv"
    p.write_text(
        "provision.init_id,provision.name,manufacturing.device_type\n"
        "SN1,,raspberrypi\n"
    )
    rows = load(str(p))
    assert rows[0]["provision"] == {"init_id": "SN1"}
    assert rows[0]["manufacturing"] == {"device_type": "raspberrypi"}


def test_load_json_flat_keys(tmp_path: Path) -> None:
    p = tmp_path / "x.json"
    p.write_text(
        json.dumps(
            [
                {
                    "provision.init_id": "SN1",
                    "manufacturing.device_type": "rpi",
                    "tenant": "tenant-a",
                }
            ]
        )
    )
    rows = load(str(p))
    assert rows[0]["provision"]["init_id"] == "SN1"
    assert rows[0]["manufacturing"]["device_type"] == "rpi"
    assert rows[0]["tenant"] == "tenant-a"


def test_load_json_nested_shape(tmp_path: Path) -> None:
    p = tmp_path / "x.json"
    p.write_text(
        json.dumps(
            [
                {
                    "provision": {"init_id": "SN1"},
                    "manufacturing": {"deviceType": "rpi"},
                }
            ]
        )
    )
    rows = load(str(p))
    assert rows[0]["provision"]["init_id"] == "SN1"
    assert rows[0]["manufacturing"]["deviceType"] == "rpi"


def test_load_stdin_requires_format(monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("[]"))
    with pytest.raises(LoaderError, match="--format is required"):
        load("-")


def test_load_stdin_with_format(monkeypatch) -> None:
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps([{"provision": {"init_id": "SN1"}}])),
    )
    rows = load("-", fmt="json")
    assert rows[0]["provision"]["init_id"] == "SN1"


def test_load_unknown_extension(tmp_path: Path) -> None:
    p = tmp_path / "x.txt"
    p.write_text("nope")
    with pytest.raises(LoaderError, match="cannot infer format"):
        load(str(p))


def test_load_missing_file() -> None:
    with pytest.raises(LoaderError, match="file not found"):
        load("/nonexistent/file.csv")


def test_load_json_must_be_array(tmp_path: Path) -> None:
    p = tmp_path / "x.json"
    p.write_text('{"not": "array"}')
    with pytest.raises(LoaderError, match="must be an array"):
        load(str(p))
