import logging

import nbformat

from app.assignment.schemas import TypeOfAssignmentFile
from app.assignment.services.dao_service import AssignmentDAO, AssignmentFileDAO
from app.dropbox.service import dropbox_service
from app.exceptions import (
    AssignmentNotFoundException,
    DecodingIPYNBException,
    IncorrectFormatAssignmentException,
    SolutionNotFoundException,
)
from app.logger import configure_logging
from app.submissions.services.notebook_service import NotebookService
from app.submissions.services.sandbox_runner import SandboxNotebookRunner
from app.submissions.services.service import SubmissionFilesDAO, SubmissionsDAO, SubmissionAttemptsDAO

logger = logging.getLogger(__name__)
configure_logging()


class SubmissionManagerService:
    @staticmethod
    async def process_and_upload_submission(
        session,
        assignment_id: str,
        submission_file,
        user_id: int,
        user_email: str,
    ):
        filename = submission_file.filename or "submission.ipynb"
        if not filename.lower().endswith(".ipynb"):
            raise IncorrectFormatAssignmentException
        submission_bytes = await submission_file.read()
        # Делегируем в bytes-вариант, чтобы upload-файл и embedded-ветка
        # проходили один и тот же pipeline исполнения/сохранения.
        return await SubmissionManagerService.process_and_upload_submission_bytes(
            session=session,
            assignment_id=assignment_id,
            submission_bytes=submission_bytes,
            user_id=user_id,
            user_email=user_email,
        )

    @staticmethod
    async def process_and_upload_submission_bytes(
        session,
        assignment_id: str,
        submission_bytes: bytes,
        user_id: int,
        user_email: str,
    ):
        # 1) Проверяем доступность задания по датам и получаем его настройки.
        assignment = await NotebookService.check_date_submission(session, assignment_id)

        # 2) Проверяем, что payload действительно декодируется как notebook.
        try:
            notebook = nbformat.reads(submission_bytes.decode("utf-8"), as_version=4)
        except Exception as e:
            raise DecodingIPYNBException from e

        # 3) Загружаем ресурсные файлы задания, которые нужны в sandbox.
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

        # 4) Выполняем notebook в изолированном Docker-контейнере.
        notebook_bytes = nbformat.writes(notebook).encode("utf-8")
        executed_notebook = nbformat.reads(
            SandboxNotebookRunner.execute_notebook(
                notebook_bytes,
                resources,
                timeout_seconds=assignment.execution_timeout_seconds,
            ).decode("utf-8"),
            as_version=4,
        )

        # 5) Ищем существующую submission-запись студента для assignment.
        submission = await SubmissionsDAO.find_one_or_none(
            session=session, user_id=user_id, assignment_id=assignment_id
        )
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

        # 6) Сохраняем уже исполненный notebook в хранилище submissions.
        submission_notebook = nbformat.writes(executed_notebook).encode("utf-8")
        upload_info = dropbox_service.upload_file(
            submission_notebook,
            filename=f"{user_id}_{assignment_id}.ipynb",
            folder_type="submissions",
        )

        # 7) Upsert записи о файле решения (SubmissionFiles).
        sub_file = await SubmissionFilesDAO.find_one_or_none(
            session=session, submission_id=submission_id
        )
        if sub_file:
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
            "User %s uploaded submission for assignment %s (%s)",
            user_email,
            assignment_id,
            upload_info["link"],
        )
        return submission_id

    @staticmethod
    async def evaluate_submission(
        session, assignment_id: str, user_email: str, submission_service
    ):
        # 1) Получаем сохраненный файл решения студента.
        submission_file = await SubmissionFilesDAO.find_one_or_none(
            session=session, submission_id=submission_service.id
        )
        if not submission_file or not submission_service:
            raise SolutionNotFoundException

        # 2) Загружаем и валидируем notebook студента.
        file_content = dropbox_service.download_file(submission_file.file_id)
        try:
            nbformat.reads(file_content.decode("utf-8"), as_version=4)
        except Exception as e:
            raise DecodingIPYNBException from e

        # 3) Загружаем оригинальный notebook преподавателя для hidden-тестов.
        assignment_file = await AssignmentFileDAO.find_one_or_none(
            session=session,
            assignment_id=assignment_id,
            file_type=TypeOfAssignmentFile.ORIGINAL,
        )
        assignment = await AssignmentDAO.find_one_or_none(session=session, id=assignment_id)
        if assignment is None or assignment_file is None:
            raise AssignmentNotFoundException

        assignment_content = dropbox_service.download_file(assignment_file.file_id)
        try:
            nbformat.reads(assignment_content.decode("utf-8"), as_version=4)
        except Exception as e:
            raise DecodingIPYNBException from e

        # 4) Подтягиваем ресурсные файлы, доступные при запуске тестов.
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

        # 5) Запускаем sandbox grading (подмена test-cell на tutor tests).
        total_points, feedback = SandboxNotebookRunner.grade_notebook(
            file_content,
            assignment_content,
            resources,
            timeout_seconds=assignment.execution_timeout_seconds,
        )

        # 6) Фиксируем результат: баллы, число попыток, индексы упавших тестов.
        next_attempt_number = submission_service.number_of_attempts + 1
        await SubmissionsDAO.update(
            session=session,
            model_id=submission_service.id,
            score=total_points,
            number_of_attempts=next_attempt_number,
            feedback=feedback,
        )

        # 7) Сохраняем историю попыток с метаданными и ссылкой на файл решения.
        await SubmissionAttemptsDAO.add(
            session=session,
            submission_id=submission_service.id,
            assignment_id=assignment_id,
            user_id=submission_service.user_id,
            attempt_number=next_attempt_number,
            score=total_points,
            feedback=feedback,
            file_id=submission_file.file_id,
            file_link=submission_file.file_link,
        )

        logger.info(
            "User %s evaluated submission for assignment %s",
            user_email,
            assignment_id,
        )
        return (total_points, feedback)
