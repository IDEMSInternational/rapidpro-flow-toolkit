import json
import logging
from pathlib import Path

from benedict import benedict
from tablib import Dataset

from rpft.parsers.universal import tabulate
from rpft.parsers.common.model_inference import model_from_headers
from rpft.parsers.common.sheetparser import SheetParser
from rpft.parsers.sheets import Sheet


LOGGER = logging.getLogger(__name__)


class JSONDataSource:

    def __init__(self, paths):
        self.objs = []

        for path in paths:
            with open(path, "r") as file_:
                self.objs += [(json.load(file_), Path(path).name)]

    def get(self, key, model=None):
        candidates = []

        for obj, name in self.objs:
            if key in obj:
                candidates += [(obj[key], name)]

        if not candidates:
            raise Exception("Data for key not found", {"key": key})

        active, name = candidates[-1]

        if len(candidates) > 1:
            LOGGER.debug(
                "Duplicate sheets found, "
                + str(
                    {
                        "name": key,
                        "readers": [name for _, name in candidates],
                        "active": name,
                    }
                ),
            )

        model = model or benedict

        return [model(**item) for item in active], name, key

    def get_all(self, key, model=None):
        model = model or benedict
        items = []

        for obj, name in self.objs:
            if key in obj:
                items += [([model(**item) for item in obj[key]], name, key)]

        return items

    def _get_sheet_or_die(self, sheet_name):
        data, meta, name, key = self._get(sheet_name)
        table = tabulate(data, meta)
        sheet = Sheet(None, name, Dataset(*table[1:], headers=table[0], title=key))

        return sheet

    def _get(self, key):
        candidates = []

        for obj, name in self.objs:
            if key in obj:
                candidates += [
                    (
                        obj[key],
                        obj.get("_idems", {}).get("tabulate", {}).get(key, {}),
                        name,
                    )
                ]

        if not candidates:
            raise Exception("Data for key not found", {"key": key})

        active, meta, name = candidates[-1]

        if len(candidates) > 1:
            LOGGER.debug(
                "Duplicate sheets found, "
                + str(
                    {
                        "name": key,
                        "readers": [name for *_, name in candidates],
                        "active": name,
                    }
                ),
            )

        return active, meta, name, key


class SheetDataSource:

    def __init__(self, readers):
        self.readers = readers

    def get(self, key, model=None):
        sheet = self._get_sheet_or_die(key)
        model = model or model_from_headers(key, sheet.table.headers)

        return SheetParser(sheet.table, model).parse_all(), sheet.reader.name, key

    def get_all(self, key, model=None):
        return [
            (
                SheetParser(
                    sheet.table,
                    model or model_from_headers(key, sheet.table.headers),
                ).parse_all(),
                sheet.reader.name,
                sheet.name,
            )
            for sheet in self._get_sheets_by_name(key)
        ]

    def _get_sheet_or_die(self, sheet_name):
        candidates = self._get_sheets_by_name(sheet_name)

        if not candidates:
            raise Exception("Sheet not found", {"name": sheet_name})

        active = candidates[-1]

        if len(candidates) > 1:
            readers = [c.reader.name for c in candidates]
            LOGGER.warning(
                "Duplicate sheets found, "
                + str(
                    {
                        "name": sheet_name,
                        "readers": readers,
                        "active": active.reader.name,
                    }
                ),
            )

        return active

    def _get_sheets_by_name(self, name):
        return [
            sheet
            for reader in self.readers
            if (sheet := reader.get_sheet(name)) is not None
        ]
