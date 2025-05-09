import json
import os

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials


# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]


def get_credentials():
    sa_creds = os.getenv("CREDENTIALS")

    if sa_creds:
        return ServiceAccountCredentials.from_service_account_info(
            json.loads(sa_creds), scopes=SCOPES
        )

    creds = None
    token_file_name = "token.json"

    if os.path.exists(token_file_name):
        creds = Credentials.from_authorized_user_file(
            token_file_name,
            scopes=SCOPES,
        )

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(token_file_name, "w") as token:
            token.write(creds.to_json())

    return creds


class Drive:

    @classmethod
    def client(cls):
        if not getattr(cls, "_client", None):
            cls._client = build("drive", "v3", credentials=get_credentials())

        return cls._client

    @classmethod
    def fetch(cls, file_id):
        params = {"fileId": file_id, "supportsAllDrives": True}
        meta = cls.client().files().get(**params).execute()
        content = cls.client().files().get_media(**params).execute()

        return meta["name"], content
