from abc import ABC, abstractmethod
import json
import os

import tablib
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


class Sheet:
    def __init__(self, reader_name, data):
        self.reader_name = reader_name
        self.data = data


class AbstractSheetReader(ABC):
    @abstractmethod
    def get_main_sheets(self):
        pass

    @abstractmethod
    def get_sheets_by_name(self, name):
        pass


class SheetDictSheetReader(AbstractSheetReader):
    '''SheetReader initialized with an attribute sheets: Dict[str, Sheet]'''

    def get_main_sheets(self):
        return self.get_sheets_by_name("content_index")

    def get_sheets_by_name(self, name):
        sheet = self.sheets.get(name)
        if sheet is None:
            return []
        return [sheet]


class CSVSheetReader(AbstractSheetReader):
    def __init__(self, filename):
        self.name = filename
        self.path = os.path.dirname(filename)
        with open(filename, mode="r", encoding="utf-8") as table_data:
            self.main_sheet = tablib.import_set(table_data, format="csv")

    def base_path(self):
        return self.path

    def get_main_sheets(self):
        return [Sheet(self.name, self.main_sheet)]

    def get_sheets_by_name(self, name):
        # Assume same path as the main sheet, and take sheet names
        # relative to that path.
        try:
            with open(
                os.path.join(self.path, f"{name}.csv"), mode="r", encoding="utf-8"
            ) as table_data:
                table = tablib.import_set(table_data, format="csv")
        except FileNotFoundError:
            table = None
        return [Sheet(self.name, table)]


class XLSXSheetReader(SheetDictSheetReader):
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
            new_row = vals[:len(data.headers)]
            if any(new_row):
                # omit empty rows
                data.append(new_row)
        return Sheet(self.name, data)


class GoogleSheetReader(SheetDictSheetReader):
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
        csv_base_paths = set()
        sheets = []
        for reader in self.sheetreaders:
            # CSV readers with the same base path share all the sheets in the
            # same folder, so we need to avoid false duplicates.
            if isinstance(reader, CSVSheetReader):
                if reader.base_path() in csv_base_paths:
                    continue
                csv_base_paths.add(reader.base_path())
            new_sheets = reader.get_sheets_by_name(name)
            sheets += new_sheets
        return sheets
