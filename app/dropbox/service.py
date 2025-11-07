import dropbox
import logging
from app.config import settings
from app.logger import configure_logging

logger = logging.getLogger(__name__)
configure_logging()

class DropboxService:
    def __init__(self):
        self.dbx = dropbox.Dropbox(
            oauth2_refresh_token=settings.DROPBOX_REFRESH_TOKEN,
            app_key=settings.DROPBOX_APP_KEY,
            app_secret=settings.DROPBOX_APP_SECRET
        )

    def upload_file(self, file_content: bytes, filename: str, folder_type: str) -> dict:
        """Загружает файл в Dropbox и возвращает путь и ссылку"""
        path = f"/{folder_type}/{filename}"
        try:
            self.dbx.files_upload(file_content, path, mode=dropbox.files.WriteMode("overwrite"))
            try:
                link = self.dbx.sharing_create_shared_link_with_settings(path).url
            except dropbox.exceptions.ApiError as e:
                # Ссылка уже есть — достаем существующую
                if (
                    isinstance(e.error, dropbox.sharing.CreateSharedLinkWithSettingsError)
                    and e.error.is_shared_link_already_exists()
                ):
                    links = self.dbx.sharing_list_shared_links(path=path, direct_only=True).links
                    if links:
                        link = links[0].url
                    else:
                        raise
                else:
                    raise
            link = link.replace("?dl=0", "?dl=1")
            return {"path": path, "link": link}
        except Exception as e:
            logger.error(f"Ошибка загрузки файла в Dropbox: {e}")
            raise

    def download_file(self, path: str) -> bytes:
        """Скачивание файла"""
        _, res = self.dbx.files_download(path)
        return res.content

    def delete_file(self, path: str) -> None:
        """Удаление файла"""
        try:
            self.dbx.files_delete_v2(path)
            logger.info(f"Файл {path} удалён из Dropbox")
        except Exception as e:
            logger.error(f"Ошибка удаления файла {path}: {e}")
            raise

dropbox_service = DropboxService()
