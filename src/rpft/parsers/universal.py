import logging
import re
from collections import defaultdict
from functools import singledispatch
from typing import Any

from benedict import benedict

from rpft.parsers.sheets import AbstractSheetReader

LOGGER = logging.getLogger(__name__)

DELIMS = "|;"
PROP_ACCESSOR = "."
META_KEY = "_idems"
TABULATE_KEY = "tabulate"
HEADERS_KEY = "headers"
Table = list[list[str]]
Book = list[tuple[str, Table]]


def bookify(data: dict) -> Book:
    """
    Convert a dict into a 'book' - a list of named tables.
    """
    meta = data.get(META_KEY, {}).get(TABULATE_KEY, {})

    return [(k, tabulate(v, meta.get(k, {}))) for k, v in data.items() if k != META_KEY]


def tabulate(data, meta: dict = {}) -> Table:
    """
    Convert a nested data structure to a tabular form
    """
    headers = meta.get(HEADERS_KEY, []) or list(
        {k: None for item in data for k, _ in item.items()}.keys()
    )
    paths = keypaths(headers)
    rows = []

    for item in data:
        obj = benedict(item)
        rows += [[stringify(obj[kp]) for kp in paths]]

    return [headers] + rows


@singledispatch
def stringify(value, **_) -> str:
    return str(value)


@stringify.register
def _(value: dict, delimiters=DELIMS) -> str:
    if len(delimiters) > 1:
        d1, d2 = delimiters
    else:
        raise ValueError("Too few delimiters to stringify dict")

    s = f" {d1} ".join(
        f"{stringify(k)}{d2} {stringify(v, delimiters=[])}" for k, v in value.items()
    )

    if len(value) == 1:
        s += " " + d1

    return s


@stringify.register
def _(value: list, delimiters=DELIMS) -> str:
    d, *delims = delimiters if delimiters else [None]

    if not d:
        raise ValueError("Too few delimiters to stringify list")

    s = f" {d} ".join(stringify(item, delimiters=delims) for item in value)

    return f"{s} {d}" if len(value) == 1 else s


@stringify.register
def _(value: tuple, delimiters=DELIMS) -> str:
    return stringify(list(value))


@stringify.register
def _(value: bool, **_) -> str:
    return str(value).lower()


def parse_tables(reader: AbstractSheetReader) -> dict:
    """
    Parse a workbook into a nested structure
    """
    obj = benedict()

    for title, sheet in reader.sheets.items():
        obj.merge(parse_table(title, sheet.table.headers, sheet.table[:]))

    return obj


def parse_table(title: str = None, headers=tuple(), rows=tuple()):
    """
    Parse data in tabular form into a nested structure
    """
    title = title or "table"

    if not headers or not rows:
        return {title: []}

    return create_obj(stream(title, headers, rows))


def stream(title: str = None, headers=tuple(), rows=tuple()):
    yield [META_KEY, TABULATE_KEY, title, HEADERS_KEY], headers

    for i, row in enumerate(rows):
        for h, v in zip(keypaths(headers), row):
            yield [title, i] + h, convert_cell(v)


def keypaths(headers):
    counters = defaultdict(int)
    indexed = []

    for key in headers:
        indexed += [(key, counters[key])]
        counters[key] += 1

    return [keypath(h, i, counters[h]) for h, i in indexed]


def keypath(header, index, count):
    expanded = [normalise_key(k) for k in header.split(PROP_ACCESSOR)]
    i = index if index < count else count - 1

    return expanded + [i] if count > 1 else expanded


def normalise_key(key):
    try:
        return int(key) - 1
    except ValueError:
        return key


def create_obj(pairs):
    obj = benedict()

    for kp, v in pairs:
        obj[kp] = v

    return obj


def convert_cell(s: str, delimiters=DELIMS) -> Any:
    if type(s) is not str:
        raise TypeError("Value to convert is not a string")

    clean = s.strip() if s else ""

    try:
        return int(clean)
    except Exception:
        pass

    try:
        return float(clean)
    except Exception:
        pass

    if clean in ("true", "false"):
        return clean == "true"

    if is_template(clean):
        return clean

    d, *delims = delimiters if delimiters else [None]

    if d and d in clean:
        seq = [convert_cell(item, delimiters=delims) for item in clean.split(d)]

        return seq[:-1] if clean and clean[-1] == d else seq

    if any(s in clean for s in delims):
        return convert_cell(clean, delimiters=delims)

    return clean


def is_template(s: str) -> bool:
    return bool(re.match("{{.*?}}|{@.*?@}|{%.*?%}", s))
