from dataclasses import dataclass
from typing import Literal


@dataclass
class CLIContext:
    instance_url: str | None
    token: str | None
    output: Literal["table", "json"]
