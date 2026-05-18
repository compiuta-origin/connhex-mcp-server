from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("connhex")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

from connhex.aio._client import AsyncConnhex  # noqa: E402
from connhex.errors import ConnhexAPIError  # noqa: E402
from connhex.sync._client import Connhex  # noqa: E402

__all__ = ["AsyncConnhex", "Connhex", "ConnhexAPIError", "__version__"]
