import asyncio
import celery
import nbformat
import logging
from datetime import date, time
from fastapi import HTTPException
from app.assignment.services.notebook_service import NotebookService
from app.dropbox.service import dropbox_service
from app.assignment.services.dao_service import (
    AssignmentService,
    AssignmentFileService,
    DisciplinesService,
)
from app.db import async_session_maker
from app.assignment.schemas import TypeOfAssignmentFile
from app.exceptions import IncorrectFormatAssignmentException
from app.logger import configure_logging

logger = logging.getLogger("assignment_manager_service")
configure_logging()


class AssignmentManagerService:
    @staticmethod
    async def process_and_upload_assignment(
        content: bytes,
        discipline_id: int,
        name: str,
        number_of_attempts: int,
        start_date: date,
        start_time: time,
        due_date: date,
        due_time: time,
        user_id,
    ):
        """
        Обрабатывает блокнот и создает задание в БД (без загрузки на dropbox).
        Возвращает ID задания и два байтовых объекта блокнотов.
        """
        notebook = NotebookService.read_notebook(content)
        NotebookService.check_notebook(notebook)
        grade = NotebookService.get_total_points(notebook)

        # исходный и модифицированный блокноты
        original_assignment = nbformat.writes(notebook).encode("utf-8")
        modified_notebook = NotebookService.modify_notebook(notebook)
        modified_assignment = nbformat.writes(modified_notebook).encode("utf-8")

        async with async_session_maker() as session:
            async with session.begin():

                assignment = await AssignmentService.add(
                    session=session,
                    discipline_id=discipline_id,
                    name=name,
                    start_date=start_date,
                    start_time=start_time,
                    due_date=due_date,
                    due_time=due_time,
                    number_of_attempts=number_of_attempts,
                    grade=grade,
                    user_id=user_id,
                )
        logger.info(f"Задание {str(assignment)} создано, загрузка файлов запущена в фоне")
        return str(assignment), original_assignment, modified_assignment


    @staticmethod
    async def upload_to_dropbox_and_finalize(assignment_id, original, modified):
        """Фоновая загрузка файлов на Google dropbox и сохранение их ID в БД"""
        logger.info(f"Файлы задания {assignment_id} начали загружаться в dropbox")
        try:
            original_file = dropbox_service.upload_file(
                file_content=original,
                filename=f"{assignment_id}_original.ipynb",
                folder_type="assignments",
            )
            logger.info(f"Оригинальный файл задания {assignment_id} загружен")
            modified_file = dropbox_service.upload_file(
                file_content=modified,
                filename=f"{assignment_id}_modified.ipynb",
                folder_type="assignments",
            )
            logger.info(f"Отредактированный файл задания {assignment_id} загружен")

            async with async_session_maker() as session:
                async with session.begin():
                    await AssignmentFileService.add(
                        session=session,
                        assignment_id=assignment_id,
                        file_type=TypeOfAssignmentFile.ORIGINAL,
                        file_id=original_file["path"],
                        file_link=original_file["link"],
                    )
                    await AssignmentFileService.add(
                        session=session,
                        assignment_id=assignment_id,
                        file_type=TypeOfAssignmentFile.MODIFIED,
                        file_id=modified_file["path"],
                        file_link=modified_file["link"],
                    )

            logger.info("Файлы задания %s успешно загружены на DropBox", assignment_id)
        except Exception as e:
            logger.error(f"Фоновая ошибка загрузки файлов для задания {assignment_id}: {e}")


    @staticmethod
    async def update_file(assignment_id, assignment_file):
        """Обновление файлов задания"""
        filename = assignment_file.filename
        if not filename.endswith(".ipynb"):
            raise IncorrectFormatAssignmentException

        content = await assignment_file.read()
        notebook = NotebookService.read_notebook(content)
        NotebookService.check_notebook(notebook)

        original_assignment = nbformat.writes(notebook).encode("utf-8")
        modified_notebook = NotebookService.modify_notebook(notebook)
        modified_assignment = nbformat.writes(modified_notebook).encode("utf-8")

        async with async_session_maker() as session:
            async with session.begin():
                # получаем текущие записи файлов
                original_record = await AssignmentFileService.find_one_or_none(
                    assignment_id=assignment_id,
                    file_type=TypeOfAssignmentFile.ORIGINAL,
                    session=session,
                )
                modified_record = await AssignmentFileService.find_one_or_none(
                    assignment_id=assignment_id,
                    file_type=TypeOfAssignmentFile.MODIFIED,
                    session=session,
                )

                # сохраняем старые файлы
                old_files_to_delete = []
                if original_record and original_record.file_id:
                    old_files_to_delete.append(original_record.file_id)
                if modified_record and modified_record.file_id:
                    old_files_to_delete.append(modified_record.file_id)

                # загружаем новые файлы на dropbox
                try:
                    original_file = dropbox_service.upload_file(
                        file_content=original_assignment,
                        filename=f"{assignment_id}_original.ipynb",
                        folder_type="assignments",
                    )
                    modified_file = dropbox_service.upload_file(
                        file_content=modified_assignment,
                        filename=f"{assignment_id}_modified.ipynb",
                        folder_type="assignments",
                    )
                except Exception as e:
                    logger.error(
                        "Ошибка загрузки новых файлов на dropbox: %s", e
                    )
                    raise HTTPException(
                        status_code=500,
                        detail="Не удалось загрузить файлы на dropbox",
                    ) from e

                # обновляем записи в БД
                await AssignmentFileService.update_or_create(
                    session=session,
                    assignment_id=assignment_id,
                    file_type=TypeOfAssignmentFile.ORIGINAL,
                    file_id=original_file["path"],
                    file_link=original_file["link"],
                )
                await AssignmentFileService.update_or_create(
                    session=session,
                    assignment_id=assignment_id,
                    file_type=TypeOfAssignmentFile.MODIFIED,
                    file_id=modified_file["path"],
                    file_link=modified_file["link"],
                )

                # обновляем оценку
                grade = NotebookService.get_total_points(notebook)
                await AssignmentService.update(
                    model_id=assignment_id, grade=grade, session=session
                )

        logger.info("Задание %s успешно обновлено", assignment_id)
        return assignment_id
