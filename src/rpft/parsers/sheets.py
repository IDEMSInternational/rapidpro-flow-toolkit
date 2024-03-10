import json
import os
from abc import ABC
from pathlib import Path
from typing import List, Mapping

import tablib
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


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

    def get_sheets_by_name(self, name) -> List[Sheet]:
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
    # If modifying these scopes, delete the file token.json.
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    def __init__(self, spreadsheet_id):
        """
        Args:
            spreadsheet_id: You can extract it from the spreadsheed URL, like this
            https://docs.google.com/spreadsheets/d/[spreadsheet_id]/edit
        """

        self.name = spreadsheet_id

        service = build("sheets", "v4", credentials=self.get_credentials())
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

    def get_credentials(self):
        sa_creds = os.getenv("CREDENTIALS")
        if sa_creds:
            return ServiceAccountCredentials.from_service_account_info(
                json.loads(sa_creds), scopes=GoogleSheetReader.SCOPES
            )

        creds = None
        token_file_name = "token.json"

        if os.path.exists(token_file_name):
            creds = Credentials.from_authorized_user_file(
                token_file_name, scopes=GoogleSheetReader.SCOPES
            )

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", GoogleSheetReader.SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(token_file_name, "w") as token:
                token.write(creds.to_json())

        return creds


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


def load_csv(path):
    with open(path, mode="r", encoding="utf-8") as csv:
        return tablib.import_set(csv, format="csv")


def load_json(path):
    with open(path, mode="r", encoding="utf-8") as fjson:
        data = json.load(fjson)
    return data


def pad(row, n):
    return row + ([""] * (n - len(row)))
