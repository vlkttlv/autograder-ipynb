import logging
import nbformat
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from nbclient import NotebookClient
from nbformat import read, NO_CONVERT
from nbclient.exceptions import CellExecutionError
from app.assignment.schemas import TypeOfAssignmentFile
from app.assignment.services.dao_service import AssignmentFileDAO
from app.exceptions import (
    DecodingIPYNBException,
    IncorrectFormatAssignmentException,
    SolutionNotFoundException,
    SyntaxException,
)
from app.submissions.services.service import (
    SubmissionFilesDAO,
    SubmissionsDAO,
)
from app.submissions.services.notebook_service import NotebookService
from app.dropbox.service import dropbox_service

from app.logger import configure_logging

logger = logging.getLogger(__name__)
configure_logging()


@contextmanager
def prepared_assignment_workspace(resource_files: list[tuple[str, bytes]]):
    """Создаёт временную рабочую директорию с файлами задания."""
    old_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp_dir:
        for filename, content in resource_files:
            target = Path(tmp_dir) / Path(filename).name
            target.write_bytes(content)
        os.chdir(tmp_dir)
        try:
            yield
        finally:
            os.chdir(old_cwd)


class SubmissionManagerService:
    @staticmethod
    async def process_and_upload_submission(
        session, assignment_id: str, submission_file, user_id: int, user_email: str
    ):
        """
        Обрабатывает блокнот, модифицирует его, загружает на Google dropbox
        и сохраняет задание в БД.
        """
        await NotebookService.check_date_submission(session, assignment_id)

        filename = submission_file.filename
        if not filename.lower().endswith(".ipynb"):
            raise IncorrectFormatAssignmentException

        notebook = read(submission_file.file, as_version=NO_CONVERT)
        client = NotebookClient(notebook, kernel_name="autograder")
        
        assignment_resources = await AssignmentFileDAO.find_all(
            session=session,
            assignment_id=assignment_id,
            file_type=TypeOfAssignmentFile.RESOURCE,
        )
        resources = [
            (
                resource.file_id.split("_resource_", 1)[-1].split("_", 1)[-1],
                dropbox_service.download_file(resource.file_id),
            )
            for resource in assignment_resources
        ]

        try:
            with prepared_assignment_workspace(resources):
                client.execute()
        except CellExecutionError as e:
            if "AssertionError" not in str(e):
                raise SyntaxException from e
        except Exception as e:
            raise SyntaxException from e

        # Проверяем наличие submission
        submission = await SubmissionsDAO.find_one_or_none(
            session=session, user_id=user_id, assignment_id=assignment_id
        )
        # если это первое решение, то добавляем его в БД
        if submission is None:
            submission_id = await SubmissionsDAO.add(
                session=session,
                user_id=user_id,
                assignment_id=assignment_id,
                score=0,
                number_of_attempts=0,
            )
        else:
            submission_id = submission.id

        # Преобразуем notebook в bytes
        submission_notebook = nbformat.writes(notebook).encode("utf-8")

        # Загружаем файл на dropbox
        upload_info = dropbox_service.upload_file(
            submission_notebook,
            filename=f"{user_id}_{assignment_id}.ipynb",
            folder_type="submissions",
        )

        # Проверяем наличие записи о файле в БД
        sub_file = await SubmissionFilesDAO.find_one_or_none(
            session=session, submission_id=submission_id
        )

        if sub_file:
            # обновляем ссылку и file_id
            await SubmissionFilesDAO.update(
                session=session,
                model_id=sub_file.id,
                file_id=upload_info["path"],
                file_link=upload_info["link"],
            )
        else:
            await SubmissionFilesDAO.add(
                session=session,
                submission_id=submission_id,
                assignment_id=assignment_id,
                file_id=upload_info["path"],
                file_link=upload_info["link"],
            )

        logger.info(
            "Пользователь %s загрузил решение для задания %s (файл %s)",
            user_email,
            assignment_id,
            upload_info["link"],
        )

        return submission_id

    @staticmethod
    async def evaluate_submission(
        session, assignment_id: str, user_email: str, submission_service
    ):
        """Проверка решения"""
        # Получаем запись о файле решения (file_id хранится в SubmissionFiles)
        submission_file = await SubmissionFilesDAO.find_one_or_none(
            session=session, submission_id=submission_service.id
        )
        if not submission_file or not submission_service:
            raise SolutionNotFoundException

        # Загружаем ipynb студента с dropbox
        file_content = dropbox_service.download_file(submission_file.file_id)
        try:
            notebook = nbformat.reads(
                file_content.decode("utf-8"), as_version=4
            )
        except Exception as e:
            raise DecodingIPYNBException from e

        # Загружаем ipynb преподавателя с dropbox
        assignment_file = await AssignmentFileDAO.find_one_or_none(
            session=session, assignment_id=assignment_id, file_type=TypeOfAssignmentFile.ORIGINAL
        )
        assignment_content = dropbox_service.download_file(
            assignment_file.file_id
        )
        try:
            tutor_notebook = nbformat.reads(
                assignment_content.decode("utf-8"), as_version=4
            )
        except Exception as e:
            raise DecodingIPYNBException from e
        
        assignment_resources = await AssignmentFileDAO.find_all(
            session=session,
            assignment_id=assignment_id,
            file_type=TypeOfAssignmentFile.RESOURCE,
        )
        resources = [
            (
                resource.file_id.split("_resource_", 1)[-1].split("_", 1)[-1],
                dropbox_service.download_file(resource.file_id),
            )
            for resource in assignment_resources
        ]

        # Проверяем
        client = NotebookClient(notebook, kernel_name="autograder")
        with prepared_assignment_workspace(resources):
            total_points, feedback = NotebookService.grade_notebook(
                client, notebook, tutor_notebook
            )

        # Обновляем результат
        await SubmissionsDAO.update(
            session=session,
            model_id=submission_service.id,
            score=total_points,
            number_of_attempts=submission_service.number_of_attempts + 1,
            feedback=feedback,
        )

        logger.info(
            "Пользователь %s проверил решение задания %s",
            user_email,
            assignment_id,
        )

        return (total_points, feedback)
