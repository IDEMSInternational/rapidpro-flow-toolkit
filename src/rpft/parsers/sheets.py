import json
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


class AbstractSheetReader(ABC):
    @property
    def sheets(self) -> Mapping[str, Sheet]:
        return self._sheets

    def get_sheet(self, name) -> Sheet:
        return self.sheets.get(name)

    def get_sheets_by_name(self, name) -> list[Sheet]:
        return [sheet] if (sheet := self.get_sheet(name)) else []


class CSVSheetReader(AbstractSheetReader):
    def __init__(self, path):
        self.name = path
        self._sheets = {
            f.stem: Sheet(reader=self, name=f.stem, table=load_csv(f))
            for f in Path(path).glob("*.csv")
        }


class JSONSheetReader(AbstractSheetReader):
    def __init__(self, filename):
        self.name = filename
        data = load_json(filename)
        self._sheets = {}
        for name, content in data["sheets"].items():
            table = tablib.Dataset()
            table.dict = content
            self._sheets[name] = Sheet(reader=self, name=name, table=table)


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
                table=self._sanitize(sheet),
            )

    def _sanitize(self, sheet):
        data = tablib.Dataset()
        data.headers = sheet.headers
        # remove trailing Nones
        while data.headers[-1] is None:
            data.headers.pop()
        for row in sheet:
            vals = tuple(str(e) if e is not None else "" for e in row)
            new_row = vals[: len(data.headers)]
            if any(new_row):
                # omit empty rows
                data.append(new_row)
        return data


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


class CompositeSheetReader:
    def __init__(self, readers=None):
        self.sheetreaders = readers or []
        self.name = "Multiple files"

    def add_reader(self, reader):
        self.sheetreaders.append(reader)

    def get_sheets_by_name(self, name):
        sheets = []

        for reader in self.sheetreaders:
            sheets += reader.get_sheets_by_name(name)

        return sheets


class DatasetSheetReader(AbstractSheetReader):
    def __init__(self, datasets, name):
        self._sheets = {d.title: Sheet(self, d.title, d) for d in datasets}
        self.name = name


def load_csv(path):
    with open(path, mode="r", encoding="utf-8") as csv:
        return tablib.import_set(csv, format="csv")


def load_json(path):
    with open(path, mode="r", encoding="utf-8") as fjson:
        data = json.load(fjson)
    return data


def pad(row, n):
    return row + ([""] * (n - len(row)))
