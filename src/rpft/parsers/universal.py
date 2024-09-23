import importlib
import logging
from collections import defaultdict
from collections.abc import Sequence
from functools import singledispatch
from typing import Any, List

from benedict import benedict

from rpft.parsers.common.cellparser import CellParser
from rpft.parsers.common.rowparser import RowParser
from rpft.parsers.common.sheetparser import SheetParser
from rpft.parsers.creation.campaigneventrowmodel import CampaignEventRowModel
from rpft.parsers.creation.contentindexrowmodel import (
    ContentIndexRowModel,
    CreateFlowRowModel,
)
from rpft.parsers.creation.triggerrowmodel import TriggerRowModel
from rpft.parsers.sheets import AbstractSheetReader, Sheet

LOGGER = logging.getLogger(__name__)

KEY_VALUE_SEP = ":"
PROP_ACCESSOR = "."
SEQ_ITEM_SEP = "|"


def parse_legacy_sheets(models_module: str, reader: AbstractSheetReader) -> dict:
    """
    Convert multiple sheets in the legacy format into a nested data structure
    """
    content_index: List[ContentIndexRowModel] = parse_content_index(
        reader,
        "content_index",
    )
    model_finder = ModelFinder(models_module)
    data = {
        "content_index": to_dict(
            parse_sheet(
                ContentIndexRowModel,
                reader.get_sheet("content_index"),
            )
        )
    }

    for entry in content_index:

        if len(entry.sheet_name) == 1:
            name = entry.sheet_name[0]
            model = model_finder.find_for_entry(entry)
            sheet = reader.get_sheet(name)

            if sheet and model:
                data[name] = to_dict(parse_sheet(model, sheet))
            else:
                LOGGER.warning(
                    "%s not found, %s",
                    "Sheet" if not sheet else "Model",
                    {"sheet": name, "model": model},
                )

    remaining = set(reader.sheets.keys()) - set(data.keys())

    for name in remaining:
        table = reader.get_sheet(name).table
        data[name] = [list(table.headers)] + [list(r) for r in table]

    LOGGER.info(
        str(
            {
                "index": {"count": len(data)},
                "sheets": {"count": len(reader.sheets)},
                "unconverted": {"count": len(remaining), "names": remaining},
            }
        )
    )

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
            RowParser(model, CellParser()),
            sheet.table,
            context=None,
        ).parse_all()
    except Exception as e:
        raise Exception(
            "Parse failed",
            {"sheet": sheet.name if sheet else None, "model": model},
            e,
        )


def to_dict(instances):
    return [
        instance.dict(
            by_alias=True,
            exclude_unset=True,
        )
        for instance in instances
    ]


class ModelFinder:
    type_model_map = {
        "content_index": ContentIndexRowModel,
        "create_campaign": CampaignEventRowModel,
        "create_flow": CreateFlowRowModel,
        "create_triggers": TriggerRowModel,
        "template_definition": CreateFlowRowModel,
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
    return [(k, tabulate(v)) for k, v in data.items()]


def tabulate(data, meta: dict = {}) -> List[List[str]]:
    """
    Convert a nested data structure to a tabular form
    """
    flattened = tabulate_data(data, meta, [])
    headers = {
        (k, v.get("meta", {}).get("alias")): None
        for item in flattened
        for k, v in item.items()
    }
    rows = [
        [item.get(h, {}).get("data", "") for h, _ in headers.keys()]
        for item in flattened
    ]

    return [[alias or name for name, alias in headers.keys()]] + rows


@singledispatch
def tabulate_data(data, meta, path):
    return create_prop(path, str(data), meta)


@tabulate_data.register
def _(data: list, meta, path):
    if len(path) > 0:
        if meta.get("layout") == "wide":
            out = dict()

            for i, item in enumerate(data, start=1):
                out = out | tabulate_data(item, meta | {"alias": path}, path + [str(i)])

            return out

        return create_prop(path, stringify(data), meta)

    rows = []

    for item in data:
        rows.append(tabulate_data(item, meta, path + ["[]"]))

    return rows


@tabulate_data.register
def _(data: dict, meta, path):
    if not path:
        raise Exception("Cannot tabulate dict to table... yet.")

    if len(path) <= 1 or meta.get("layout") == "wide":
        out = dict()

        for k, v in data.items():
            out = out | tabulate_data(v, meta.get(k, {}), path + [k])

        return out

    return create_prop(path, stringify(data), meta)


@tabulate_data.register
def _(data: bool, meta, path):
    return create_prop(path, str(data).lower(), meta)


def create_prop(path, data, meta={}) -> dict:
    if meta.get("alias"):
        meta["alias"] = ".".join(meta["alias"][1:])

    key = ".".join(path[1:])

    return {key: {"meta": meta, "data": data}}


@singledispatch
def stringify(value) -> str:
    return str(value)


@stringify.register
def _(value: dict) -> str:
    return " | ".join(
        "{0}: {1}".format(stringify(k), stringify(v)) for k, v in value.items()
    )


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
    return [
        parse_table(title, sheet.table.headers, sheet.table[:])
        for title, sheet in reader.sheets.items()
    ]


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
    yield [("_idems", "tabulate", title, "headers"), headers]

    counters = defaultdict(int)
    hs = []

    for key in headers:
        hs += [(key, counters[key])]
        counters[key] += 1

    hs = [create_keypath(h, i, counters[h]) for h, i in hs]

    for i, row in enumerate(rows):
        for h, v in zip(hs, row):
            yield [[title, i] + h, convert_cell(v)]


def create_keypath(header, index, count):
    expanded = header.split(PROP_ACCESSOR)
    i = index if index < count else count - 1

    return expanded + [i] if count > 1 else expanded


def create_obj(pairs):
    obj = benedict()

    for kp, v in pairs:
        obj[kp] = v

    return dict(obj)


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

    if recursive and KEY_VALUE_SEP in s:
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
