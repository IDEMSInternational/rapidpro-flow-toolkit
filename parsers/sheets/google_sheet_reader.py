import tablib
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import os

class GoogleSheetReader:

    # If modifying these scopes, delete the file token.json.
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

    def __init__(self, spreadsheet_id):
        '''
        Args:
            spreadsheet_id: You can extract it from the spreadsheed URL, like this
            https://docs.google.com/spreadsheets/d/[spreadsheet_id]/edit
        '''

        # Authentication code nabbed from
        # https://developers.google.com/sheets/api/quickstart/python
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', GoogleSheetReader.SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # TODO: Provide instructions how to obtain this file and get access
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', GoogleSheetReader.SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = sheet_metadata.get('sheets', '')
        titles = []
        for sheet in sheets:
            title = sheet.get("properties", {}).get("title", "Sheet1")
            titles.append(title)

        result = service.spreadsheets().values().batchGet(
                spreadsheetId=spreadsheet_id, ranges=titles).execute()

        self.main_sheet = None
        self.sheets = {}
        for sheet in result.get('valueRanges', []):
            name = sheet.get('range', '').split('!')[0]
            if name.startswith("'") and name.endswith("'"):
                name = name[1:-1]
            content = sheet.get('values', [])
            if name == 'content_index':
                self.main_sheet = self._table_from_content(content)
            elif name in self.sheets:
                raise ValueError(f"Warning: Duplicate sheet name: {name}")
            else:
                self.sheets[name] = self._table_from_content(content)

        if self.main_sheet is None:
            raise ValueError(f'{filename} must have a sheet "content_index"')

    def _table_from_content(self, content):
        table = tablib.Dataset()
        table.headers = content[0]
        n_headers = len(table.headers)
        for row in content[1:]:
            # Pad row to proper length
            table.append(row + ([''] * (n_headers - len(row))))
        return table

    def get_main_sheet(self):
        return self.main_sheet

    def get_sheet(self, name):
        return self.sheets[name]