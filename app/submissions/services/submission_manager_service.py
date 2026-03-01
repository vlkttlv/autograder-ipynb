import logging
import nbformat
from nbformat import read, NO_CONVERT
from app.assignment.schemas import TypeOfAssignmentFile
from app.assignment.services.dao_service import AssignmentDAO, AssignmentFileDAO
from app.exceptions import (
    AssignmentNotFoundException,
    DecodingIPYNBException,
    IncorrectFormatAssignmentException,
    SolutionNotFoundException,
)
from app.submissions.services.service import (
    SubmissionFilesDAO,
    SubmissionsDAO,
)
from app.submissions.services.notebook_service import NotebookService
from app.submissions.services.sandbox_runner import SandboxNotebookRunner
from app.dropbox.service import dropbox_service

from app.logger import configure_logging

logger = logging.getLogger(__name__)
configure_logging()



class SubmissionManagerService:
    @staticmethod
    async def process_and_upload_submission(
        session, assignment_id: str, submission_file, user_id: int, user_email: str
    ):
        """
        Обрабатывает блокнот, модифицирует его, загружает на Google dropbox
        и сохраняет задание в БД.
        """
        assignment = await NotebookService.check_date_submission(session, assignment_id)

        filename = submission_file.filename
        if not filename.lower().endswith(".ipynb"):
            raise IncorrectFormatAssignmentException

        notebook = read(submission_file.file, as_version=NO_CONVERT)
        
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

        notebook_bytes = nbformat.writes(notebook).encode("utf-8")
        notebook = nbformat.reads(
            SandboxNotebookRunner.execute_notebook(
                notebook_bytes,
                resources,
                timeout_seconds=assignment.execution_timeout_seconds,
            ).decode("utf-8"),
            as_version=4,
        )

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
            nbformat.reads(file_content.decode("utf-8"), as_version=4)
        except Exception as e:
            raise DecodingIPYNBException from e

        # Загружаем ipynb преподавателя с dropbox
        assignment_file = await AssignmentFileDAO.find_one_or_none(
            session=session, assignment_id=assignment_id, file_type=TypeOfAssignmentFile.ORIGINAL
        )
        assignment = await AssignmentDAO.find_one_or_none(session=session, id=assignment_id)
        if assignment is None:
            raise AssignmentNotFoundException

        assignment_content = dropbox_service.download_file(
            assignment_file.file_id
        )
        try:
            nbformat.reads(assignment_content.decode("utf-8"), as_version=4)
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

        # Проверяем в изолированном эфемерном контейнере
        total_points, feedback = SandboxNotebookRunner.grade_notebook(
            file_content,
            assignment_content,
            resources,
            timeout_seconds=assignment.execution_timeout_seconds,
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
