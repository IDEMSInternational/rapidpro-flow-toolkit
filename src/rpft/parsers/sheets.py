import json
import re
from abc import ABC
from collections.abc import Mapping
from pathlib import Path

import tablib
from googleapiclient.discovery import build

from rpft.google import get_credentials


class SheetReaderError(Exception):
    pass


class Sheet:
    def __init__(self, reader, name, table):
        self.reader = reader
        self.name = name
        self.table = table

    def __repr__(self):
        return f"Sheet(name: '{self.name}')"


class AbstractSheetReader(ABC):
    @property
    def sheets(self) -> Mapping[str, Sheet]:
        return self._sheets

    def get_sheet(self, name) -> Sheet:
        return self.sheets.get(name)

    @classmethod
    def can_process(cls, path):
        return False

    def __repr__(self):
        return f"{type(self).__name__}(name: '{self.name}')"


class CSVSheetReader(AbstractSheetReader):
    def __init__(self, path):
        self.name = path
        self._sheets = {
            f.stem: Sheet(reader=self, name=f.stem, table=load_csv(f))
            for f in Path(path).glob("*.csv")
        }

    @classmethod
    def can_process(cls, location):
        return Path(location).is_dir()


class JSONSheetReader(AbstractSheetReader):
    def __init__(self, filename):
        self.name = filename
        data = load_json(filename)
        self._sheets = {}
        for name, content in data["sheets"].items():
            table = tablib.Dataset()
            table.dict = content
            self._sheets[name] = Sheet(reader=self, name=name, table=table)

    @classmethod
    def can_process(cls, location):
        if Path(location).suffix.lower() == ".json":
            return "sheets" in load_json(location)

        return False


class XLSXSheetReader(AbstractSheetReader):
    def __init__(self, filename):
        self.name = filename
        with open(filename, "rb") as table_data:
            data = tablib.Databook().load(table_data.read(), "xlsx")
        self._sheets = {}
        for sheet in data.sheets():
            self.sheets[sheet.title] = Sheet(
                reader=self,
                name=sheet.title,
                table=sanitize(sheet),
            )

    @classmethod
    def can_process(cls, location):
        return Path(location).suffix.lower() == ".xlsx"


class GoogleSheetReader(AbstractSheetReader):

    def __init__(self, spreadsheet_id):
        """
        Args:
            spreadsheet_id: You can extract it from the spreadsheed URL, like this
            https://docs.google.com/spreadsheets/d/[spreadsheet_id]/edit
        """

        self.name = spreadsheet_id

        service = build("sheets", "v4", credentials=get_credentials())
        sheet_metadata = (
            service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        )
        sheets = sheet_metadata.get("sheets", "")
        titles = []
        for sheet in sheets:
            title = sheet.get("properties", {}).get("title", "Sheet1")
            titles.append(title)

        result = (
            service.spreadsheets()
            .values()
            .batchGet(spreadsheetId=spreadsheet_id, ranges=titles)
            .execute()
        )

        self._sheets = {}
        for sheet in result.get("valueRanges", []):
            name = sheet.get("range", "").split("!")[0]
            if name.startswith("'") and name.endswith("'"):
                name = name[1:-1]
            content = sheet.get("values", [])
            if name in self._sheets:
                raise ValueError(f"Warning: Duplicate sheet name: {name}")
            else:
                self._sheets[name] = Sheet(
                    reader=self,
                    name=name,
                    table=self._table_from_content(content),
                )

    def _table_from_content(self, content):
        table = tablib.Dataset()
        table.headers = content[0]

        for row in content[1:]:
            table.append(self._prepare_row(row, len(table.headers)))

        return table

    def _prepare_row(self, row, max_cols):
        return pad(
            [cell.replace("\r\n", "\n") for cell in row],
            max_cols,
        )

    @classmethod
    def can_process(cls, location):
        return bool(re.fullmatch(r"[a-z0-9_-]{44}", location, re.IGNORECASE))


class DatasetSheetReader(AbstractSheetReader):
    def __init__(self, datasets, name):
        self._sheets = {d.title: Sheet(self, d.title, d) for d in datasets}
        self.name = "[datasets]"


class ODSSheetReader(AbstractSheetReader):
    def __init__(self, path):
        book = tablib.Databook()

        with open(path, "rb") as f:
            book.load(f, format="ods")

        self._sheets = {
            sheet.title: Sheet(self, sheet.title, sanitize(sheet))
            for sheet in book.sheets()
        }
        self.name = str(path)

    @classmethod
    def can_process(cls, location):
        return Path(location).suffix.lower() == ".ods"


def sanitize(sheet):
    data = tablib.Dataset()
    data.headers = sheet.headers
    # remove trailing Nones
    while data.headers and data.headers[-1] is None:
        data.headers.pop()
    for row in sheet:
        vals = tuple(str(e) if e is not None else "" for e in row)
        new_row = vals[: len(data.headers)]
        if any(new_row):
            # omit empty rows
            data.append(new_row)
    return data


def load_csv(path):
    with open(path, mode="r", encoding="utf-8") as csv:
        return tablib.import_set(csv, format="csv")


def load_json(path):
    with open(path, mode="r", encoding="utf-8") as fjson:
        data = json.load(fjson)
    return data


def pad(row, n):
    return row + ([""] * (n - len(row)))
