from typing import Any

from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def render(obj: Any, fmt: str) -> None:
    if fmt == "json":
        if isinstance(obj, BaseModel):
            print(obj.model_dump_json(indent=2))
        elif isinstance(obj, list):
            import json

            print(
                json.dumps(
                    [
                        o.model_dump() if isinstance(o, BaseModel) else o
                        for o in obj
                    ],
                    indent=2,
                    default=str,
                )
            )
        elif isinstance(obj, dict):
            import json

            print(json.dumps(obj, indent=2, default=str))
        else:
            print(obj)
        return

    if isinstance(obj, BaseModel):
        _render_model(obj)
    elif isinstance(obj, list):
        _render_list(obj)
    elif isinstance(obj, dict):
        _render_dict(obj)
    else:
        console.print(obj)


def _render_model(obj: BaseModel) -> None:
    data = obj.model_dump()
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Field", style="bold cyan")
    table.add_column("Value")
    for k, v in data.items():
        table.add_row(k, _fmt_value(v))
    console.print(Panel(table, expand=False))


def _render_list(items: list) -> None:
    if not items:
        console.print("[dim]No results.[/dim]")
        return

    first = items[0]
    if isinstance(first, BaseModel):
        rows = [item.model_dump() for item in items]
        columns = _columns_for(rows)
        table = Table()
        for col in columns:
            table.add_column(col, overflow="fold")
        for row in rows:
            table.add_row(*[_fmt_value(row.get(k)) for k in columns])
        console.print(table)
    elif isinstance(first, dict):
        columns = _columns_for(items)
        table = Table()
        for col in columns:
            table.add_column(col, overflow="fold")
        for item in items:
            table.add_row(*[_fmt_value(item.get(k)) for k in columns])
        console.print(table)
    else:
        for item in items:
            console.print(item)


def _render_dict(d: dict) -> None:
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Field", style="bold cyan")
    table.add_column("Value")
    for k, v in d.items():
        table.add_row(str(k), _fmt_value(v))
    console.print(Panel(table, expand=False))


def _columns_for(rows: list[dict]) -> list[str]:
    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                columns.append(key)
    return columns


def _fmt_value(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        import json

        return json.dumps(v, default=str)
    return str(v)
