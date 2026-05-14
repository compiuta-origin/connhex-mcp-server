from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("connhex-sdk")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

from connhex_sdk.connhex import AsyncConnhex  # noqa: E402
from connhex_sdk.errors import ConnhexAPIError  # noqa: E402

__all__ = ["AsyncConnhex", "ConnhexAPIError", "__version__"]
