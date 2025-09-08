import json
import os

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from datetime import datetime


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

    @classmethod
    def get_modified_time(cls, file_id_ls):
        if type(file_id_ls) is str:
            file_id_ls = [file_id_ls]

        modified_time_dict = {}

        def modified_time_callback(request_id, response, exception):
            if exception is None:
                file_id = response.get('id')
                modified_time_str = response.get('modifiedTime')
                if modified_time_str.endswith("Z"):
                    modified_time_str = modified_time_str[:-1] + "+00:00"
                modified_time_dict[file_id] = datetime.fromisoformat(modified_time_str)
            else:
                raise exception
            
        batch = cls.client().new_batch_http_request(callback=modified_time_callback)

        for file_id in file_id_ls:
            batch.add(cls.client().files().get(fileId=file_id, 
                fields='id,modifiedTime', supportsAllDrives=True)
            )

        batch.execute()

        return modified_time_dict
        