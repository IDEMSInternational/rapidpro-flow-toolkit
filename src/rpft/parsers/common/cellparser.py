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
        return self.cleanse(output)

    def cleanse(self, nested_list):
        # Unescape escaped characters
        TEMP_CHARACTER = "\1"
        if type(nested_list) is str:
            string = nested_list.strip()
            string = string.replace(CellParser.ESCAPE_CHARACTER * 2, TEMP_CHARACTER)
            for sep in CellParser.SEPARATORS:
                string = string.replace(CellParser.ESCAPE_CHARACTER + sep, sep)
            string = string.replace(TEMP_CHARACTER, CellParser.ESCAPE_CHARACTER)
            return string
        else:
            return [self.cleanse(item) for item in nested_list]

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
                string[locations[i] + 1: locations[i + 1]]
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

    def parse_as_string(self, value, context={}, is_object=None):
        # If context is None, template parsing is omitted entirely.
        # is_object is a pass-by-reference boolean, realised via
        # the class BooleanWrapper, to indicate to the caller
        # whether the parsing result represents an object that
        # is not to be processed any further.
        if value is None:
            return ""
        value = str(value)
        if context is None or (not context and "{" not in value):
            # This is a hacky optimization.
            return value
        stripped_value = value.strip()
        env = self.env
        if stripped_value.startswith("{@") and stripped_value.endswith("@}"):
            # Special case: Return a python object rather than a string,
            # if possible.
            # Ensure this is a single template, not e.g. '{@ x @} {@ y @}'
            if not stripped_value[2:].find("{@") == -1:
                LOGGER.critical(
                    'Cell may not contain nested "{{@" templates.'
                    f'Cell content: "{stripped_value}"'
                )
            if is_object is not None:
                is_object.boolean = True
            env = self.native_env

        try:
            template = env.from_string(stripped_value)
            return template.render(context)
        except Exception as e:
            LOGGER.critical(
                f'Error while parsing cell "{stripped_value}" with context "{context}":'
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
