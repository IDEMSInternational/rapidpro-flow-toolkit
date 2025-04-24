import json
import logging
from collections import ChainMap
from logging.config import dictConfig
from pathlib import Path

from rpft.logger import DEFAULT_CONFIG


logger = logging.getLogger(__name__)


class LoggingContextHandler:
    def __init__(self):
        self.context_variables = []
        self.processing_stack = []

    def add(self, processing_unit, **new_context_vars):
        self.processing_stack.append(processing_unit)
        self.context_variables.append(new_context_vars)

    def get_processing_stack(self):
        return self.processing_stack

    def get_context_variables(self):
        # Union of all the dicts
        return dict(ChainMap(*self.context_variables))

    def pop(self):
        self.processing_stack.pop()
        self.context_variables.pop()


_context = LoggingContextHandler()


class logging_context:
    def __init__(self, processing_unit, **kwargs):
        self.processing_unit = processing_unit
        self.kwargs = kwargs

    def __enter__(self):
        _context.add(self.processing_unit, **self.kwargs)

    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type is None:
            _context.pop()


class ContextFilter(logging.Filter):

    def filter(self, record):
        record.processing_stack = " | ".join(_context.get_processing_stack())
        record.context_variables = _context.get_context_variables()
        return True


def initialize_main_logger(file_path="errors.log", config_path="logging.json"):
    config = None

    if Path(config_path).exists():
        with open(config_path, "r") as f:
            config = json.load(f)
    else:
        config = dict(DEFAULT_CONFIG)

    config["handlers"]["file"]["filename"] = file_path
    dictConfig(config)
    logger.debug(f"Logging configured, config={config}")
