from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("connhex")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

from connhex.aio._client import AsyncConnhex  # noqa: E402
from connhex.errors import ConnhexAPIError  # noqa: E402

__all__ = ["AsyncConnhex", "ConnhexAPIError", "__version__"]
