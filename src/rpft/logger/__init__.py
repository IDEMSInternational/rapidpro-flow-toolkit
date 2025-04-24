DEFAULT_CONFIG = {
    "disable_existing_loggers": False,
    "filters": {
        "context": {
            "()": "rpft.logger.logger.ContextFilter",
        }
    },
    "formatters": {
        "default": {
            "format": "%(levelname)s:%(name)s: %(processing_stack)s: %(message)s",
        },
    },
    "handlers": {
        "file": {
            "class": "logging.FileHandler",
            "filename": "errors.log",
            "filters": ["context"],
            "formatter": "default",
            "level": "INFO",
            "mode": "w",
        },
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["context"],
            "formatter": "default",
            "level": "CRITICAL",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": [
            "file",
            "console",
        ],
    },
    "version": 1,
}
