import json
import logging
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
        "stderr": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stderr",
        }
    },
    "loggers": {
        "connhex_cli": {"level": "DEBUG", "propagate": True},
        "connhex_sdk": {"level": "DEBUG", "propagate": True},
        "httpcore": {"level": "WARNING", "propagate": True},
        "httpx": {"level": "WARNING", "propagate": True},
    },
    "root": {
        "level": "WARNING",
        "handlers": ["stderr"],
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
