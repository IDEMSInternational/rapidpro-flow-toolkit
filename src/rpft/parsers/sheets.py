import json
import os
from abc import ABC
from pathlib import Path

import tablib
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


class SheetReaderError(Exception):
    pass


class Sheet:
    def __init__(self, reader_name, data):
        self.reader_name = reader_name
        self.data = data


class AbstractSheetReader(ABC):
    def get_main_sheets(self):
        return self.get_sheets_by_name("content_index")

    def get_sheets_by_name(self, name):
        return [sheet] if (sheet := self.sheets.get(name)) else []


class CSVSheetReader(AbstractSheetReader):
    def __init__(self, path, main="content_index"):
        self.path = Path(path)
        self.main = main
        self.sheets = {
            f.stem: Sheet(self.name, load_csv(f)) for f in self.path.glob("*.csv")
        }

        if not self.main_sheet:
            raise SheetReaderError(
                "Main sheet not found",
                {"file": str(self.path), "sheet": self.main},
            )

    @property
    def main_sheet(self):
        return self.get_sheet(self.main)

    @property
    def name(self):
        return self.path.stem

    def get_sheet(self, name):
        return self.sheets.get(name)


class XLSXSheetReader(AbstractSheetReader):
    def __init__(self, filename):
        self.name = filename
        with open(filename, "rb") as table_data:
            data = tablib.Databook().load(table_data.read(), "xlsx")
        self.sheets = {}
        for sheet in data.sheets():
            self.sheets[sheet.title] = self._sanitize(sheet)

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
        return Sheet(self.name, data)


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

        self.sheets = {}
        for sheet in result.get("valueRanges", []):
            name = sheet.get("range", "").split("!")[0]
            if name.startswith("'") and name.endswith("'"):
                name = name[1:-1]
            content = sheet.get("values", [])
            if name in self.sheets:
                raise ValueError(f"Warning: Duplicate sheet name: {name}")
            else:
                self.sheets[name] = self._table_from_content(content)

    def _table_from_content(self, content):
        table = tablib.Dataset()
        table.headers = content[0]
        n_headers = len(table.headers)
        for row in content[1:]:
            # Pad row to proper length
            table.append(row + ([""] * (n_headers - len(row))))
        return Sheet(self.name, table)

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

    def get_main_sheets(self):
        sheets = []
        for reader in self.sheetreaders:
            sheets += reader.get_main_sheets()
        return sheets

    def get_sheets_by_name(self, name):
        sheets = []

        for reader in self.sheetreaders:
            sheets += reader.get_sheets_by_name(name)

        return sheets


def load_csv(path):
    with open(path, mode="r", encoding="utf-8") as csv:
        return tablib.import_set(csv, format="csv")
