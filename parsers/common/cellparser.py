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
        if not context:
            # This is an optimization.
            # However, it also means that we don't notice if there are
            # uninstantiated template vars in this particular case.
            return value
        else:
            return Template(value).render(context)
