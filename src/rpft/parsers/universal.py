import importlib
import logging
import re
from collections import defaultdict
from collections.abc import Sequence
from functools import singledispatch
from typing import Any, List

from benedict import benedict

from rpft.parsers.common.cellparser import TemplatePreserver
from rpft.parsers.common.rowparser import RowParser
from rpft.parsers.common.sheetparser import SheetParser
from rpft.parsers.creation.campaigneventrowmodel import CampaignEventRowModel
from rpft.parsers.creation.contentindexrowmodel import ContentIndexRowModel
from rpft.parsers.creation.flowrowmodel import FlowTemplateStatement
from rpft.parsers.creation.triggerrowmodel import TriggerRowModel
from rpft.parsers.sheets import AbstractSheetReader, Sheet

LOGGER = logging.getLogger(__name__)

KEY_VALUE_SEP = ":"
PROP_ACCESSOR = "."
SEQ_ITEM_SEP = "|"
DEINDEX_PATTERN = re.compile(r"(.*)\.\d+")
META_KEY = "_idems"
TABULATE_KEY = "tabulate"
HEADERS_KEY = "headers"


def parse_legacy_sheets(models_module: str, reader: AbstractSheetReader) -> dict:
    """
    Convert multiple sheets in the legacy format into a nested data structure
    """
    content_index: List[ContentIndexRowModel] = {
        entry.sheet_name[0]: entry
        for entry in parse_content_index(
            reader,
            "content_index",
        )
        if len(entry.sheet_name) == 1
    }
    model_finder = ModelFinder(models_module)
    data = {}
    meta = {}
    unconverted = []

    for name, sheet in reader.sheets.items():
        if name in content_index:
            model = model_finder.find_for_entry(content_index[name])

            if sheet and model:
                data[name] = to_dicts(parse_sheet(model, sheet))
            else:
                LOGGER.warning(
                    "%s not found, %s",
                    "Sheet" if not sheet else "Model",
                    {"sheet": name, "model": model},
                )
        elif name == "content_index":
            data[name] = to_dicts(parse_sheet(ContentIndexRowModel, sheet))
        else:
            data[name] = [list(sheet.table.headers)] + [list(r) for r in sheet.table]
            unconverted += [name]

        meta[name] = {HEADERS_KEY: sheet.table.headers}

    LOGGER.info(
        str(
            {
                "index": {"count": len(data)},
                "sheets": {"count": len(reader.sheets)},
                "unconverted": {"count": len(unconverted), "names": unconverted},
            }
        )
    )

    data[META_KEY] = {TABULATE_KEY: meta}

    return data


def parse_content_index(reader, name):
    content_index: List[ContentIndexRowModel] = parse_sheet(
        ContentIndexRowModel,
        reader.get_sheet(name),
    )
    acc = []

    for entry in content_index:
        acc += [entry]

        if entry.type == "content_index":
            acc += parse_content_index(reader, entry.sheet_name[0])

    return acc


def parse_sheet(model, sheet: Sheet):
    try:
        return SheetParser(
            RowParser(model, TemplatePreserver()),
            sheet.table,
            context=None,
        ).parse_all()
    except Exception as e:
        raise Exception(
            "Parse failed",
            {"sheet": sheet.name if sheet else None, "model": model},
            e,
        )


def to_dicts(instances):
    objs = []

    for instance in instances:
        obj = instance.dict(by_alias=True, exclude_unset=True)

        if "template_argument_definitions" in obj:
            obj["template_arguments"] = obj.pop("template_argument_definitions")

        objs += [obj]

    return objs


class ModelFinder:
    type_model_map = {
        "content_index": ContentIndexRowModel,
        "create_campaign": CampaignEventRowModel,
        "create_flow": FlowTemplateStatement,
        "create_triggers": TriggerRowModel,
        "template_definition": FlowTemplateStatement,
    }

    def __init__(self, module=None):
        self._module = importlib.import_module(module) if module else None

    def find_for_entry(self, entry):
        if entry.type in self.type_model_map:
            return self.type_model_map.get(entry.type)

        if entry.data_model:
            try:
                return getattr(self._module, entry.data_model)
            except AttributeError:
                pass

        return None


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
    yield [(META_KEY, TABULATE_KEY, title, HEADERS_KEY), headers]

    for i, row in enumerate(rows):
        for h, v in zip(keypaths(headers), row):
            yield [[title, i] + h, convert_cell(v)]


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


def convert_cell(s: str, recursive=True) -> Any:
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

    if recursive and KEY_VALUE_SEP in s and SEQ_ITEM_SEP in s:
        try:
            props = [p.split(KEY_VALUE_SEP, 1) for p in s.split(SEQ_ITEM_SEP) if p]

            return {k.strip(): convert_cell(v, recursive=False) for k, v in props}
        except Exception:
            pass

    if recursive and SEQ_ITEM_SEP in s:
        try:
            return [
                convert_cell(item, recursive=False)
                for item in s.split(SEQ_ITEM_SEP)
                if item
            ]
        except Exception:
            pass

    return clean
