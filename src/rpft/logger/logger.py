import logging
from collections import ChainMap
import sys


LOGGER_NAME = "main"


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


logging_context_handler = LoggingContextHandler()


class logging_context:
    def __init__(self, processing_unit, **kwargs):
        self.processing_unit = processing_unit
        self.kwargs = kwargs

    def __enter__(self):
        logging_context_handler.add(self.processing_unit, **self.kwargs)

    def __exit__(self, exc_type, exc_value, exc_tb):
        logging_context_handler.pop()


class ContextFilter(logging.Filter):
    def __init__(self):
        super(ContextFilter, self).__init__()

    def filter(self, record):
        record.processing_stack = " | ".join(
            logging_context_handler.get_processing_stack()
        )
        record.context_variables = logging_context_handler.get_context_variables()
        return True


class ShutdownHandler(logging.FileHandler):
    def emit(self, record):
        super().emit(record)
        if record.levelno >= logging.CRITICAL:
            # raise Exception(self.format(record))
            print(f"{self.format(record)}", file=sys.stderr)
            sys.exit(1)


def get_logger():
    return logging.getLogger(LOGGER_NAME)


def initialize_main_logger():
    LOGGER = logging.getLogger(LOGGER_NAME)
    LOGGER.setLevel(logging.INFO)
    context_filter = ContextFilter()
    LOGGER.addFilter(context_filter)
    # We're currently not using the context_variables, so don't print them.
    # If needed, add "Context: %(context_variables)s" to the format string below
    stdout_formatter = logging.Formatter(
        "%(levelname)s: %(processing_stack)s: %(message)s\n"
    )
    stdout_handler = ShutdownHandler("errors.log", "w")
    stdout_handler.setFormatter(stdout_formatter)
    LOGGER.addHandler(stdout_handler)
    return LOGGER
