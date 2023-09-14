from jinja2 import Environment
from jinja2.nativetypes import NativeEnvironment
from jinja2 import contextfilter
from rpft.logger.logger import get_logger, logging_context

LOGGER = get_logger()


class CellParser:
    class BooleanWrapper:
        def __init__(self, val=False):
            self.boolean = val

    def escape_string(string):
        return string.replace("\\", "\\\\").replace("|", "\\|").replace(";", "\\;")

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
        l1 = self.split_by_separator(string, "|")
        if type(l1) == str:
            output = self.split_by_separator(string, ";")
        else:
            output = [self.split_by_separator(s, ";") for s in l1]
        return self.cleanse(output)

    def cleanse(self, nested_list):
        # Unescape escaped characters (\, |, ;)
        if type(nested_list) == str:
            return (
                nested_list.strip()
                .replace("\\\\", "\1")
                .replace("\\|", "|")
                .replace("\\;", ";")
                .replace("\1", "\\")
            )
        else:
            return [self.cleanse(l) for l in nested_list]

    def split_by_separator(self, string, sep):
        pos = 0
        sep_locations = []
        while pos < len(string):
            c = string[pos]
            if c == "\\":
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
                    f'Cell may not contain nested "{{@" templates. Cell content: "{stripped_value}"'
                )
            if is_object is not None:
                is_object.boolean = True
            env = self.native_env

        try:
            template = env.from_string(stripped_value)
            return template.render(context)
        except Exception as e:
            LOGGER.critical(
                f'Error while parsing cell "{stripped_value}" with context "{context}": {str(e)}'
            )
