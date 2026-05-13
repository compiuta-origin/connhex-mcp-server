"""Load connectables from a CSV/JSON file or stdin.

Output is a list of dicts ready for ConnectablesBatch.model_validate.
The shape mirrors the legacy Go CLI: flat dotted keys (`provision.X`,
`manufacturing.X`, top-level `tenant`) are unflattened into the nested
`{provision, manufacturing, tenant}` form.
"""

import csv
import io
import json
import sys
from pathlib import Path
from typing import Any

PROVISION_PREFIX = "provision."
MANUFACTURING_PREFIX = "manufacturing."


class LoaderError(ValueError):
    pass


def load(source: str, fmt: str | None = None) -> list[dict[str, Any]]:
    """Load connectables from a path or `-` (stdin).

    `fmt` ("csv" | "json") is required for stdin; otherwise inferred from
    the file extension.
    """
    if source == "-":
        if fmt is None:
            raise LoaderError(
                "--format is required when reading from stdin (-)"
            )
        text = sys.stdin.read()
        return _parse(text, fmt)

    path = Path(source)
    if not path.exists():
        raise LoaderError(f"file not found: {source}")
    if fmt is None:
        ext = path.suffix.lower().lstrip(".")
        if ext not in {"csv", "json"}:
            raise LoaderError(
                f"cannot infer format from extension '{path.suffix}'; "
                f"pass --format csv|json"
            )
        fmt = ext
    return _parse(path.read_text(), fmt)


def _parse(text: str, fmt: str) -> list[dict[str, Any]]:
    if fmt == "csv":
        return _parse_csv(text)
    if fmt == "json":
        return _parse_json(text)
    raise LoaderError(f"unsupported format: {fmt}")


def _parse_csv(text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict[str, Any]] = []
    # csv data rows start at line 2 (line 1 is the header).
    for i, raw in enumerate(reader, start=2):
        rows.append(_unflatten({k.strip(): v for k, v in raw.items()}, row=i))
    return rows


def _parse_json(text: str) -> list[dict[str, Any]]:
    data = json.loads(text)
    if not isinstance(data, list):
        raise LoaderError("JSON input must be an array of objects")
    rows: list[dict[str, Any]] = []
    for i, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise LoaderError(f"JSON item {i} is not an object")
        rows.append(_unflatten(item, row=i))
    return rows


def _unflatten(flat: dict[str, Any], *, row: int) -> dict[str, Any]:
    """Unflatten dotted keys into nested provision/manufacturing dicts.

    Also accepts an already-nested input shape (objects under `provision`
    and `manufacturing`). The two shapes can mix; nested wins on conflict.
    """
    provision: dict[str, Any] = {}
    manufacturing: dict[str, Any] = {}
    tenant: Any = None

    for key, value in flat.items():
        if value is None or (isinstance(value, str) and value == ""):
            continue
        if key.startswith(PROVISION_PREFIX):
            provision[key[len(PROVISION_PREFIX) :]] = value
        elif key.startswith(MANUFACTURING_PREFIX):
            manufacturing[key[len(MANUFACTURING_PREFIX) :]] = value
        elif key == "provision" and isinstance(value, dict):
            provision = {**provision, **value}
        elif key == "manufacturing" and isinstance(value, dict):
            manufacturing = {**manufacturing, **value}
        elif key == "tenant":
            tenant = value
        # Unknown top-level keys are dropped silently to match Go.

    out: dict[str, Any] = {
        "provision": provision,
        "manufacturing": manufacturing,
        "row": row,
    }
    if tenant is not None:
        out["tenant"] = tenant
    return out
