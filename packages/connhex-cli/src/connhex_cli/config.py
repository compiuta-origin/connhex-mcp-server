from typing import Literal

from connhex_sdk.config import CoreSettings


class CLISettings(CoreSettings):
    output: Literal["table", "json"] = "table"
    log_config: str | None = None
