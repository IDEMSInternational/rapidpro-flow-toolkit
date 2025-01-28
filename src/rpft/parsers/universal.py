import logging
import re
from collections import defaultdict
from collections.abc import Sequence
from functools import singledispatch
from typing import Any, List

from benedict import benedict
from lark import Lark, Transformer

from rpft.parsers.sheets import AbstractSheetReader

LOGGER = logging.getLogger(__name__)

KEY_VALUE_SEP = ";"
PROP_ACCESSOR = "."
SEQ_ITEM_SEP = "|"
META_KEY = "_idems"
TABULATE_KEY = "tabulate"
HEADERS_KEY = "headers"
CELL_GRAMMAR = r"""
?start    : TEMPLATE -> template
          | seq
          | item

seq       : (item? "|" item?)+

?item     : subseq
          | value

subseq    : (value? ";" value?)+

?value    : NUMBER  -> number
          | BOOLEAN -> boolean
          | STRING  -> string
          |         -> empty

NUMBER    : SIGNED_NUMBER

BOOLEAN   : "true"
          | "false"

TEMPLATE  : /.*{[{@%].*/

STRING    : /(\\[|;]|[^|;])+/

%import common (SIGNED_NUMBER, WS)
%ignore WS
"""
PARSER = Lark(CELL_GRAMMAR)


def create_workbook(data: dict) -> list:
    meta = data.pop(META_KEY, {}).get(TABULATE_KEY, {})

    return [(k, tabulate(v, meta.get(k, {}))) for k, v in data.items()]


def tabulate(data, meta: dict = {}) -> List[List[str]]:
    """
    Convert a nested data structure to a tabular form
    """
    if all(type(item) is list for item in data):
        return data

    headers = meta.get(HEADERS_KEY, []) or list(
        {k: None for item in data for k, v in item.items()}.keys()
    )
    rows = []

    for item in data:
        obj = benedict(item)
        rows += [[stringify(obj[kp]) for kp in keypaths(headers)]]

    return [headers] + rows


@singledispatch
def stringify(value) -> str:
    return str(value)


@stringify.register
def _(value: dict) -> str:

    s = " | ".join(
        f"{stringify(k)}{KEY_VALUE_SEP} {stringify(v)}" for k, v in value.items()
    )

    if len(value) == 1:
        s += " " + SEQ_ITEM_SEP

    return s


@stringify.register
def _(value: list) -> str:
    return " | ".join(stringify(i) for i in value)


@stringify.register
def _(value: bool) -> str:
    return str(value).lower()


def parse_tables(reader: AbstractSheetReader) -> dict:
    """
    Parse a workbook into a nested structure
    """
    obj = benedict()

    for title, sheet in reader.sheets.items():
        obj.merge(parse_table(title, sheet.table.headers, sheet.table[:]))

    return obj


def parse_table(
    title: str = None,
    headers: Sequence[str] = tuple(),
    rows: Sequence[Sequence[str]] = tuple(),
):
    """
    Parse data in tabular form into a nested structure
    """
    title = title or "table"

    if not headers or not rows:
        return {title: []}

    return create_obj(stream(title, headers, rows))


def stream(
    title: str = None,
    headers: Sequence[str] = tuple(),
    rows: Sequence[Sequence[str]] = tuple(),
):
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


def convert_cell(s: str, delimiters=["|", ";"]) -> Any:
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

    delim, *delims = delimiters if delimiters else [None]

    if delim and delim in clean:
        seq = [convert_cell(item, delimiters=delims) for item in clean.split(delim)]

        return seq[:-1] if clean and clean[-1] == delim else seq

    if any(s in clean for s in delims):
        return convert_cell(clean, delimiters=delims)

    return clean


def is_template(s: str) -> bool:
    return bool(re.match("{{.*?}}|{@.*?@}|{%.*?%}", s))


class CellTransformer(Transformer):

    seq = subseq = list

    def boolean(self, tokens):
        return (tokens[0]).strip() == "true"

    def empty(self, tokens):
        return ""

    def number(self, tokens):
        token = (tokens[0]).strip()

        try:
            return int(token)
        except Exception:
            pass

        try:
            return float(token)
        except Exception:
            pass

        raise Exception(f"Conversion to number failed, token={token}")

    def string(self, tokens):
        return re.sub(r"\\(.{1})", r"\g<1>", tokens[0].strip())

    def template(self, tokens):
        return self.string(tokens)


def parse_cell(cell: str) -> Any:
    if type(cell) is not str:
        raise TypeError("Value to convert must be a string")

    return CellTransformer().transform(PARSER.parse(cell)) if cell else ""
