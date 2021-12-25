import re
import uuid
from collections import defaultdict
from enum import Enum


class CellType(Enum):
    OBJECT = 'object'
    TEXT = 'text'


def generate_uuid():
    return str(uuid.uuid4())


def generate_new_uuid():
    return str(uuid.uuid4())


def get_cell_type_for_column_header(header):
    if re.search('^condition:(\d+)', header):
        return CellType.OBJECT

    return CellType.TEXT


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


def find_node(nodes_map, from_row_id, condition):
    for _, node in nodes_map.items():
        from_row_ids = node._from.split(';')

        if (from_row_id in from_row_ids) and node.condition == condition:
            return node


def find_node_with_row_id_only(nodes_map, from_row_id):
    for _, node in nodes_map.items():
        from_row_ids = node._from.split(';')

        if from_row_id in from_row_ids:
            return node
