import json
import os

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials


EXT_MIME_TYPE = {
    ".ods": "application/vnd.oasis.opendocument.spreadsheet",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

ALL_SCOPES = SCOPES + [
    "https://www.googleapis.com/auth/devstorage.read_write",
]


def get_credentials(scopes = None):
    scopes = scopes or SCOPES

    sa_creds = os.getenv("CREDENTIALS")

    if sa_creds:
        return ServiceAccountCredentials.from_service_account_info(
            json.loads(sa_creds), scopes=scopes
        )

    creds = None
    token_file_name = "token.json"

    if os.path.exists(token_file_name):
        creds = Credentials.from_authorized_user_file(
            token_file_name,
            scopes=scopes,
        )

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", ALL_SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(token_file_name, "w") as token:
            token.write(creds.to_json())

        # Load the credentials with only the scopes needed for this task
        creds = Credentials.from_authorized_user_file(
            token_file_name,
            scopes=scopes,
        )

    return creds


class Drive:

    @classmethod
    def client(cls):
        if not getattr(cls, "_client", None):
            cls._client = build("drive", "v3", credentials=get_credentials())

        return cls._client

    @classmethod
    def meta(cls, file_id):
        return (
            cls.client()
            .files()
            .get(
                fileId=file_id,
                supportsAllDrives=True,
            )
            .execute()
        )

    @classmethod
    def fetch(cls, file_id):
        meta = cls.meta(file_id)
        content = (
            cls.client()
            .files()
            .get_media(
                fileId=file_id,
                supportsAllDrives=True,
            )
            .execute()
        )

        return meta["name"], content

    @classmethod
    def export(cls, file_id, ext=None, mime_type=None):
        try:
            mime = mime_type if mime_type else EXT_MIME_TYPE[ext]
        except KeyError:
            raise ValueError("Failed to determine MIME type for export")

        meta = cls.meta(file_id)
        content = (
            cls.client()
            .files()
            .export(
                fileId=file_id,
                mimeType=mime,
            )
            .execute()
        )

        return meta["name"], content
