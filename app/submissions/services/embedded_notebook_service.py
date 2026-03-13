import re
import json
import httpx
import asyncio
import logging
from typing import Any
from pathlib import PurePosixPath
from urllib.parse import quote

from sqlalchemy.ext.asyncio import AsyncSession

from app.assignment.schemas import TypeOfAssignmentFile
from app.assignment.services.dao_service import AssignmentFileDAO
from app.config import settings
from app.exceptions import (
    AssignmentNotFoundException,
    EmbeddedEditorDisabledException,
    NotebookEditorUnavailableException,
)
from app.dropbox.service import dropbox_service
from app.submissions.services.notebook_service import NotebookService
from app.user.models import Users

logger = logging.getLogger(__name__)


class JupyterHubClient:
    """Клиент для взаимодействия бэкенда с JupyterHub

    Используется на стороне бэкенда для:
    - управления пользователем и их серверами в JupyterHub
    - выпуска короткоживущего токена пользователя
    - чтения b записи блокнота через Contents API пользовательского сервера
    """
    def __init__(self):
        self.origin = settings.JUPYTERHUB_ORIGIN.rstrip("/")
        self.public_base = settings.JUPYTERHUB_PUBLIC_BASE_URL.rstrip("/")
        self.admin_token = settings.JUPYTERHUB_ADMIN_TOKEN
        self.token_ttl_seconds = settings.JUPYTERHUB_TOKEN_TTL_SECONDS
        
        if not self.admin_token:
            raise NotebookEditorUnavailableException
        
        self.api_base = f"{self.origin}{self.public_base}/hub/api"

    @property
    def _headers(self) -> dict[str, str]:
        """Заголовки авторизации для запросов к API JupyterHub"""
        return {"Authorization": f"token {self.admin_token}"}

    async def _request(
        self,
        method: str,
        url: str,
        expected_codes: tuple[int, ...],
        **kwargs: Any,
    ) -> httpx.Response:
        """Унифицированный метод отправки HTTP-запросов в API JupyterHub

        Выполняет запрос, проверяет код ответа и в случае ошибки
        генерирует исключение недоступности редактора
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.request(
                    method, url, headers=self._headers, **kwargs
                )
        except httpx.HTTPError as e:
            logger.error("Ошибка запроса к JupyterHub: %s %s", method, url)
            raise NotebookEditorUnavailableException from e

        if response.status_code not in expected_codes:
            logger.error(
                "Неожиданный код ответа JupyterHub: %s для %s %s, body=%s",
                response.status_code,
                method,
                url,
                response.text,
            )
            raise NotebookEditorUnavailableException
        return response

    async def ensure_user(self, username: str):
        """Проверяет существование пользователя в JupyterHub и при необходимости создаёт его"""
        user_url = f"{self.api_base}/users/{username}"
        res = await self._request("GET", user_url, expected_codes=(200, 404))
        if res.status_code == 404:
            await self._request("POST", user_url, expected_codes=(201,))

    async def ensure_server_ready(self, username: str, server_name: str):
        """Запускает пользовательский сервер и ожидает его готовности"""
        server_url = f"{self.api_base}/users/{username}/servers/{quote(server_name, safe='')}"
        await self._request("POST", server_url, expected_codes=(201, 202, 400, 409))


        user_url = f"{self.api_base}/users/{username}"
        # Периодически проверяем состояние сервера
        for _ in range(40):
            res = await self._request("GET", user_url, expected_codes=(200,))
            payload = res.json()
            ready = payload.get("servers", {}).get(server_name, {}).get("ready", False)
            if ready:
                return
            await asyncio.sleep(0.5)
        raise NotebookEditorUnavailableException

    async def create_user_token(self, username: str) -> str:
        """Создаёт временный токен пользователя для работы в браузере и обращения к Contents API"""
        token_url = f"{self.api_base}/users/{username}/tokens"
        res = await self._request(
            "POST",
            token_url,
            expected_codes=(200, 201),
            json={
                "note": "autograder-embedded-editor",
                "expires_in": self.token_ttl_seconds,
            },
        )
        token = res.json().get("token")
        if not token:
            raise NotebookEditorUnavailableException
        return token

    @staticmethod
    def _user_server_base_url(
        origin: str, public_base: str, username: str, server_name: str
    ) -> str:
        """Формирует базовый URL пользовательского сервера Jupyter"""
        return (
            f"{origin}{public_base}/user/{quote(username, safe='@')}/"
            f"{quote(server_name, safe='')}"
        )

    def build_iframe_url(
        self,
        username: str,
        server_name: str,
        notebook_path: str,
        user_token: str,
    ) -> str:
        """Формирует URL для открытия блокнота JupyterHub внутри iframe"""
        quoted_path = quote(notebook_path, safe="/")
        public_origin = settings.JUPYTERHUB_PUBLIC_ORIGIN.rstrip("/")
        user_server_base = self._user_server_base_url(
            public_origin, self.public_base, username, server_name
        )
        return f"{user_server_base}/lab/tree/{quoted_path}?token={user_token}"

    async def put_notebook(
        self,
        username: str,
        server_name: str,
        notebook_path: str,
        notebook_bytes: bytes,
        user_token: str,
    ):
        """Записывает файл блокнота на пользовательский сервер через Contents API"""
        # Перед записью убеждаемся, что все каталоги пути существуют
        await self._ensure_parent_directories(
            username, server_name, notebook_path, user_token
        )
        user_server_base = self._user_server_base_url(
            self.origin, self.public_base, username, server_name
        )
        contents_url = (
            f"{user_server_base}/api/contents/{quote(notebook_path, safe='/')}"
        )
        try:
            # Contents API принимает содержимое блокнота в виде JSON
            content = json.loads(notebook_bytes.decode("utf-8"))
        except Exception as e:
            raise NotebookEditorUnavailableException from e

        headers = {"Authorization": f"token {user_token}"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.put(
                    contents_url,
                    headers=headers,
                    json={"type": "notebook", "format": "json", "content": content},
                )
        except httpx.HTTPError as e:
            raise NotebookEditorUnavailableException from e

        if response.status_code not in (200, 201):
            logger.error(
                "Ошибка сохранения блокнота в Jupyter: %s, body=%s",
                response.status_code,
                response.text,
            )
            raise NotebookEditorUnavailableException
    
    async def put_file(
        self,
        username: str,
        server_name: str,
        file_path: str,
        file_bytes: bytes,
        user_token: str,
    ):
        """Записывает файл на пользовательский сервер через Contents API"""
        await self._ensure_parent_directories(
            username, server_name, file_path, user_token
        )
        user_server_base = self._user_server_base_url(
            self.origin, self.public_base, username, server_name
        )
        contents_url = (
            f"{user_server_base}/api/contents/{quote(file_path, safe='/')}"
        )
        headers = {"Authorization": f"token {user_token}"}
        text_content = file_bytes.decode("utf-8", errors="replace")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.put(
                    contents_url,
                    headers=headers,
                    json={"type": "file", "format": "text", "content": text_content},
                )
        except httpx.HTTPError as e:
            raise NotebookEditorUnavailableException from e

        if response.status_code not in (200, 201):
            logger.error(
                "Ошибка сохранения файла в Jupyter: %s, body=%s",
                response.status_code,
                response.text,
            )
            raise NotebookEditorUnavailableException
        

    async def _ensure_parent_directories(
        self, username: str, server_name: str, notebook_path: str, user_token: str
    ):
        """Создаёт отсутствующие каталоги в пути к блокноту"""
        parts = [p for p in notebook_path.split("/")[:-1] if p]
        if not parts:
            return

        user_server_base = self._user_server_base_url(
            self.origin, self.public_base, username, server_name
        )
        headers = {"Authorization": f"token {user_token}"}
        current = []
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                for part in parts:
                    current.append(part)
                    dir_path = "/".join(current)
                    dir_url = f"{user_server_base}/api/contents/{quote(dir_path, safe='/')}"
                    check = await client.get(dir_url, headers=headers)
                    if check.status_code == 200:
                        continue
                    if check.status_code != 404:
                        logger.error(
                            "Ошибка проверки каталога Jupyter: %s, body=%s",
                            check.status_code,
                            check.text,
                        )
                        raise NotebookEditorUnavailableException

                    create = await client.put(
                        dir_url,
                        headers=headers,
                        json={"type": "directory"},
                    )
                    if create.status_code not in (200, 201):
                        logger.error(
                            "Ошибка создания каталога Jupyter: %s, body=%s",
                            create.status_code,
                            create.text,
                        )
                        raise NotebookEditorUnavailableException
        except httpx.HTTPError as e:
            raise NotebookEditorUnavailableException from e

    async def get_notebook(
        self,
        username: str,
        server_name: str,
        notebook_path: str,
        user_token: str,
    ) -> bytes:
        """Читает notebook и возвращает его в bytes"""
        user_server_base = self._user_server_base_url(
            self.origin, self.public_base, username, server_name
        )
        contents_url = f"{user_server_base}/api/contents/{quote(notebook_path, safe='/')}"
        headers = {"Authorization": f"token {user_token}"}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(contents_url, headers=headers)
        except httpx.HTTPError as e:
            raise NotebookEditorUnavailableException from e

        if response.status_code != 200:
            logger.error(
                "Ошибка чтения блокнота из Jupyter: %s, body=%s",
                response.status_code,
                response.text,
            )
            raise NotebookEditorUnavailableException

        payload = response.json()
        content = payload.get("content")
        if not content:
            raise NotebookEditorUnavailableException
        if isinstance(content, dict):
            return json.dumps(content, ensure_ascii=False).encode("utf-8")
        if isinstance(content, str):
            return content.encode("utf-8")
        raise NotebookEditorUnavailableException


class EmbeddedNotebookService:
    """Сервис работы с блокнотом внутри интерфейса приложения"""

    @staticmethod
    def ensure_enabled():
        """Проверяет, включён ли встроенный редактор блокнотов"""
        if not settings.ENABLE_EMBEDDED_NOTEBOOK_EDITOR:
            raise EmbeddedEditorDisabledException

    @staticmethod
    def hub_username(user: Users) -> str:
        """Формирует имя пользователя для JupyterHub"""
        return user.email.strip().lower()

    @staticmethod
    def notebook_path(assignment_id: str) -> str:
        """Путь к файлу блокнота внутри пользовательского сервера Jupyter"""
        return f"assignments/{assignment_id}/{settings.JUPYTER_NOTEBOOK_FILENAME}"

    @staticmethod
    def server_name(assignment_id: str) -> str:
        """Генерирует корректное имя сервера на основе идентификатора задания"""
        normalized = re.sub(r"[^a-zA-Z0-9-]+", "-", assignment_id).strip("-").lower()
        return normalized or "assignment"

    @staticmethod
    def draft_dropbox_path(assignment_id: str, user_id: int) -> str:
        """Путь черновика блокнота в Dropbox"""
        return f"/drafts/{assignment_id}/{user_id}/{settings.JUPYTER_NOTEBOOK_FILENAME}"

    @staticmethod
    def _resource_file_name(assignment_id: str, dropbox_path: str) -> str:
        """Возвращает имя ресурса, убирая служебный префикс, добавленный при загрузке."""
        name = PurePosixPath(dropbox_path).name
        prefix = re.compile(rf"^{re.escape(assignment_id)}_resource_\d+_")
        return prefix.sub("", name, count=1) or name

    @classmethod
    async def _sync_resource_files(
        cls,
        session: AsyncSession,
        assignment_id: str,
        username: str,
        server_name: str,
        user_token: str,
        client: JupyterHubClient,
    ):
        """Копирует дополнительные файлы задания в папку Jupyter рядом с notebook."""
        resources = await AssignmentFileDAO.find_all(
            session=session,
            assignment_id=assignment_id,
            file_type=TypeOfAssignmentFile.RESOURCE,
        )
        base_dir = f"assignments/{assignment_id}"
        for resource in resources:
            resource_name = cls._resource_file_name(assignment_id, resource.file_id)
            resource_bytes = dropbox_service.download_file(resource.file_id)
            await client.put_file(
                username=username,
                server_name=server_name,
                file_path=f"{base_dir}/{resource_name}",
                file_bytes=resource_bytes,
                user_token=user_token,
            )


    @classmethod
    async def _seed_draft_if_needed(
        cls,
        session: AsyncSession,
        assignment_id: str,
        user_id: int,
    ) -> bytes:
        """Получает черновик из Dropbox или создаёт его из исходного файла задания"""

        draft_path = cls.draft_dropbox_path(assignment_id, user_id)
        # Если черновик уже существует - используем его
        if dropbox_service.file_exists(draft_path):
            return dropbox_service.download_file(draft_path)
        # Иначе берём файл задания
        assignment_file = await AssignmentFileDAO.find_one_or_none(
            session=session,
            assignment_id=assignment_id,
            file_type=TypeOfAssignmentFile.MODIFIED,
        )
        if not assignment_file:
            assignment_file = await AssignmentFileDAO.find_one_or_none(
                session=session,
                assignment_id=assignment_id,
                file_type=TypeOfAssignmentFile.ORIGINAL,
            )
        if not assignment_file:
            raise AssignmentNotFoundException

        content = dropbox_service.download_file(assignment_file.file_id)
        # Первичное заполнение черновика, чтобы студент видел стартовый блокнот
        dropbox_service.upload_file_to_path(content, draft_path)
        return content

    @classmethod
    async def create_session(
        cls,
        session: AsyncSession,
        assignment_id: str,
        current_user: Users,
    ) -> dict[str, Any]:
        """Создает сессию и возвращает URL iframe"""
        cls.ensure_enabled()
        await NotebookService.check_date_submission(session, assignment_id)

        notebook_bytes = await cls._seed_draft_if_needed(
            session, assignment_id, current_user.id
        )
        notebook_path = cls.notebook_path(assignment_id)
        server_name = cls.server_name(assignment_id)
        username = cls.hub_username(current_user)
        # Последовательность: пользователь - сервер - токен - загрузка notebook
        client = JupyterHubClient()
        await client.ensure_user(username)
        await client.ensure_server_ready(username, server_name)
        user_token = await client.create_user_token(username)
        await client.put_notebook(
            username, server_name, notebook_path, notebook_bytes, user_token
        )
        await cls._sync_resource_files(
            session=session,
            assignment_id=assignment_id,
            username=username,
            server_name=server_name,
            user_token=user_token,
            client=client,
        )
        return {
            "enabled": True,
            "iframe_url": client.build_iframe_url(
                username, server_name, notebook_path, user_token
            ),
            "notebook_path": notebook_path,
            "autosave_interval_sec": settings.JUPYTER_NOTEBOOK_AUTOSAVE_SECONDS,
        }

    @classmethod
    async def save_draft(
        cls,
        session: AsyncSession,
        assignment_id: str,
        current_user: Users,
        jupyter_token: str,
    ) -> bytes:
        """Сохраняет текущий блокнот из Jupyter обратно в Dropbox как черновик"""
        cls.ensure_enabled()
        await NotebookService.check_date_submission(session, assignment_id)

        username = cls.hub_username(current_user)
        server_name = cls.server_name(assignment_id)
        notebook_path = cls.notebook_path(assignment_id)
        
        client = JupyterHubClient()
        notebook_bytes = await client.get_notebook(
            username, server_name, notebook_path, jupyter_token
        )
        # сохраняем черновик
        dropbox_service.upload_file_to_path(
            notebook_bytes, cls.draft_dropbox_path(assignment_id, current_user.id)
        )
        return notebook_bytes
