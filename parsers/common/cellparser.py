from collections import defaultdict

from jinja2 import Template
from jinja2.nativetypes import NativeEnvironment

def get_separators(value):
    # TODO: Discuss escape characters
    separators = ['|', ';', ':']

    found_separators = [s for s in separators if s in value]
    iterator = iter(found_separators)

    return [next(iterator, None) for _ in range(0, 3)]


def get_object_from_cell_value(value):
    separator_1, separator_2, _ = get_separators(value)
    obj = defaultdict(str)

    members = value.split(separator_1)
    for member in members:
        key, value = member.split(separator_2)
        obj[key] = value
    return obj


class CellParser:

    def __init__(self):
        self.native_env = NativeEnvironment(variable_start_string='{@', variable_end_string='@}')

    def parse(self, value, context={}):
        value = self.parse_as_string(value, context)

        # TODO: Implement properly
        if ';' in value:
            return value.split(';')
        else:
            return value

    def parse_as_string(self, value, context={}):
        if not context and '{' not in value:
            # This is a hacky optimization.
            return value
        stripped_value = value.strip()
        if stripped_value.startswith('{@') and stripped_value.endswith('@}'):
            # Special case: Return a python object rather than a string,
            # if possible.
            template = self.native_env.from_string(stripped_value)
            return template.render(context)
        else:
            return Template(value).render(context)
