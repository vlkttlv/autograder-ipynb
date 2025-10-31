import os
import io
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# OAuth2 client credentials
CREDENTIALS_FILE = "app/credentials/credentials.json"
TOKEN_FILE = "app/credentials/token.pickle"

# ID папок в Google Drive (создай вручную и вставь значения)
ASSIGNMENTS_FOLDER_ID = "1uGPK9z_BRnJH575xd6OSSdZso-SpqzvS"
SUBMISSIONS_FOLDER_ID = "1QBh9Y-VThFd9_3mGoHPedu08Pe8SxEKo"

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

class DriveService:
    def __init__(self):
        self.service = self._authorize()

    def _authorize(self):
        creds = None
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "rb") as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
            with open(TOKEN_FILE, "wb") as token:
                pickle.dump(creds, token)
        return build("drive", "v3", credentials=creds)

    def upload_file(self, file_content: bytes, filename: str, folder_type: str) -> dict:
        """Загрузка файла в Google Drive (в зависимости от типа папки)"""
        folder_id = (
            ASSIGNMENTS_FOLDER_ID if folder_type == "assignments" else SUBMISSIONS_FOLDER_ID
        )
        file_metadata = {"name": filename, "parents": [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype="application/x-ipynb+json")
        file = (
            self.service.files()
            .create(body=file_metadata, media_body=media, fields="id, webViewLink")
            .execute()
        )
        return {"id": file.get("id"), "link": file.get("webViewLink")}

    def download_file(self, file_id: str) -> bytes:
        """Скачивание файла по ID"""
        request = self.service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.seek(0)
        return fh.read()
    
    
    def delete_file(self, file_id: str) -> None:
        """
        Удаляет файл на Google Drive по его ID.

        Args:
            file_id (str): ID файла на Google Drive

        Raises:
            HttpError: Если произошла ошибка при удалении
        """
        try:
            self.service.files().delete(fileId=file_id).execute()
        except Exception as e:
            # можно логировать ошибку
            print(f"Ошибка при удалении файла {file_id}: {e}")
            raise

drive_service = DriveService()
