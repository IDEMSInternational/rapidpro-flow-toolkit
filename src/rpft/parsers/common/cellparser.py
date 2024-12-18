import re

from jinja2 import Environment, contextfilter
from jinja2.nativetypes import NativeEnvironment

from rpft.logger.logger import get_logger

LOGGER = get_logger()


class CellParserError(Exception):
    pass


class CellParser:
    class BooleanWrapper:
        def __init__(self, val=False):
            self.boolean = val

    # Separators by level
    # Note: split_into_lists currently assumes there are exactly two separators.
    SEPARATORS = ["|", ";"]
    ESCAPE_CHARACTER = "\\"

    def escape_string(string):
        string = string.replace(
            CellParser.ESCAPE_CHARACTER, CellParser.ESCAPE_CHARACTER * 2
        )
        for sep in CellParser.SEPARATORS:
            string = string.replace(sep, CellParser.ESCAPE_CHARACTER + sep)
        return string

    @contextfilter
    def evaluate_string(context, string):
        return eval(string, {}, context)

    def __init__(self):
        self.env = Environment()
        self.env.filters["escape"] = CellParser.escape_string
        self.env.filters["eval"] = CellParser.evaluate_string
        self.native_env = NativeEnvironment(
            variable_start_string="{@", variable_end_string="@}"
        )
        self.native_env.filters["escape"] = CellParser.escape_string
        self.native_env.filters["eval"] = CellParser.evaluate_string

    def split_into_lists(self, string):
        l1 = self.split_by_separator(string, CellParser.SEPARATORS[0])
        if type(l1) is str:
            output = self.split_by_separator(string, CellParser.SEPARATORS[1])
        else:
            output = [self.split_by_separator(s, CellParser.SEPARATORS[1]) for s in l1]
        return unescape(output)

    def split_by_separator(self, string, sep):
        pos = 0
        sep_locations = []
        while pos < len(string):
            c = string[pos]
            if c == CellParser.ESCAPE_CHARACTER:
                pos += 1
            elif c == sep:
                sep_locations.append(pos)
            pos += 1
        if not sep_locations:
            # No separators found: return a string, not a list
            return string
        else:
            if len(string) - 1 in sep_locations:
                # Special case: Last character is a separator.
                # Here we don't put '' at the end of the list
                locations = [-1] + sep_locations[:-1] + [len(string) - 1]
            else:
                locations = [-1] + sep_locations + [len(string)]
            return [
                string[locations[i] + 1 : locations[i + 1]]
                for i in range(len(locations) - 1)
            ]

    def parse(self, value, context={}):
        is_object = CellParser.BooleanWrapper()
        value = self.parse_as_string(value, context, is_object)
        # {@ @} templating returns an object that is not processed further.
        if is_object.boolean:
            return value
        else:
            return self.split_into_lists(value)

    def parse_as_string(self, value, context={}, is_object: BooleanWrapper = None):
        # is_object indicates to the caller whether the parsing result represents an
        # object that is not to be processed any further.
        if value is None:
            return ""

        stripped = str(value).strip()

        if context is None or (not context and "{" not in stripped):
            return stripped

        env = self.env

        # Special case: Return a Python object rather than a string, if possible.
        if stripped.startswith("{@") and stripped.endswith("@}"):
            env = self.native_env

            # Ensure this is a single template, not e.g. '{@ x @} {@ y @}'
            if not stripped[2:].find("{@") == -1:
                LOGGER.critical(
                    'Cell may not contain nested "{{@" templates.'
                    f'Cell content: "{stripped}"'
                )

            if is_object is not None:
                is_object.boolean = True

        try:
            return env.from_string(stripped).render(context)
        except Exception as e:
            LOGGER.critical(
                f'Error while parsing cell "{stripped}" with context "{context}":'
                f" {str(e)}"
            )

    def join_from_lists(self, value, depth=0):
        if type(value) is str:
            return CellParser.escape_string(value)
        elif type(value) in [int, bool, float]:
            return str(value)
        elif type(value) is list:
            if depth > len(CellParser.SEPARATORS):
                raise CellParserError(
                    "Error while converting nested list into string: "
                    "Input list is nested too deeply."
                )
            if len(value) == 1:
                # Trailing separator to distinguish 1-element lists from basic types
                return (
                    self.join_from_lists(value[0], depth=depth + 1)
                    + CellParser.SEPARATORS[depth]
                )
            return CellParser.SEPARATORS[depth].join(
                [self.join_from_lists(e, depth=depth + 1) for e in value]
            )
        else:
            raise CellParserError(
                "Error while converting nested list into string: "
                "Invalid type of list element."
            )


def unescape(nested_list):
    """Unescape escaped characters"""
    return (
        re.sub(r"\\(.{1})", r"\g<1>", nested_list.strip())
        if type(nested_list) is str
        else [unescape(item) for item in nested_list]
    )
