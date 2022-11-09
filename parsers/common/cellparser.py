from collections import defaultdict

from jinja2 import Template


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
    def parse(self, value, context={}):
        value = self.parse_as_string(value, context)

        # TODO: Implement properly
        if ';' in value:
            return value.split(';')
        else:
            return value

    def parse_as_string(self, value, context={}):
        return Template(value).render(context)
