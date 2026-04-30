import json
import logging.config

_DEFAULT_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        }
    },
    "handlers": {
        "stdout": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        }
    },
    "loggers": {
        "uvicorn": {"level": "INFO", "propagate": True},
        "uvicorn.access": {"level": "INFO", "propagate": True},
        "uvicorn.error": {"level": "INFO", "propagate": True},
        "fastmcp": {"level": "INFO", "propagate": True},
        "mcp": {"level": "INFO", "propagate": True},
        "connhex_mcp": {"level": "DEBUG", "propagate": True},
        "sse_starlette.sse": {"level": "WARNING", "propagate": True},
        "httpcore": {"level": "WARNING", "propagate": True},
        "httpx": {"level": "WARNING", "propagate": True},
        "urllib3": {"level": "WARNING", "propagate": True},
    },
    "root": {
        "level": "DEBUG",
        "handlers": ["stdout"],
    },
}


def setup_logging(path: str | None = None) -> dict:
    if path:
        with open(path) as f:
            config = json.load(f)
    else:
        config = _DEFAULT_CONFIG
    logging.config.dictConfig(config)
    return config
