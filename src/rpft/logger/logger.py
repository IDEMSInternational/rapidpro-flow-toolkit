import logging
from collections import ChainMap


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


def initialize_main_logger(file_path="errors.log"):
    context_filter = ContextFilter()

    file_handler = logging.FileHandler(file_path, "w")
    file_handler.addFilter(context_filter)

    console_handler = logging.StreamHandler()
    console_handler.addFilter(context_filter)
    console_handler.setLevel(logging.CRITICAL)

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s:%(name)s: %(processing_stack)s: %(message)s",
        handlers=[file_handler, console_handler],
    )
