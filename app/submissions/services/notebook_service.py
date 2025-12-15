from datetime import datetime
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.assignment.services.dao_service import AssignmentDAO
from app.exceptions import (
    AssignmentNotFoundException,
    DeadlineException,
    EndedAttemptsException,
    SolutionNotFoundException,
)
import re
from nbclient.exceptions import CellExecutionError
from app.logger import configure_logging
from app.submissions.services.service import SubmissionsDAO

logger = logging.getLogger(__name__)
configure_logging()


class NotebookService:
    @staticmethod
    async def check_date_submission(session: AsyncSession, assignment_id):
        now_datetime = datetime.now()
        assignment = await AssignmentDAO.find_one_or_none(session=session, id=assignment_id)

        if not assignment:
            raise AssignmentNotFoundException

        if (
            assignment.due_date < now_datetime.date()
            or assignment.start_date > now_datetime.date()
        ):
            raise DeadlineException

    @staticmethod
    async def check_date_and_attempts_submission(session, assignment_id, current_user):
        now_datetime = datetime.now()
        assignment = await AssignmentDAO.find_one_or_none(session=session, id=assignment_id)

        if not assignment:
            raise AssignmentNotFoundException

        if (
            assignment.due_date < now_datetime.date()
            or assignment.start_date > now_datetime.date()
        ):
            raise DeadlineException

        submission_service = await SubmissionsDAO.find_one_or_none(
            session=session, user_id=current_user.id, assignment_id=assignment_id
        )
        if not submission_service:
            raise SolutionNotFoundException

        if (
            submission_service.number_of_attempts
            == assignment.number_of_attempts
        ):
            raise EndedAttemptsException

        return submission_service

    @staticmethod
    def grade_notebook(client, submission, tutor_notebook):
        total_points = 0
        feedback = []
        # Выполняем каждую ячейку отдельно
        with client.setup_kernel() as kernel:
            for index, cell in enumerate(submission.cells):
                if (
                    cell.cell_type == "code"
                ):  # Проверяем, что это кодовая ячейка
                    try:
                        client.execute_cell(
                            cell, cell_index=index, store_history=True
                        )
                    except CellExecutionError as e:
                        logger.error(f"ОШИБКА: {e}")
                    if cell.cell_type == "code":
                        if (
                            "# Tests " in cell.source
                            and " points." in cell.source
                        ):
                            points = 0
                            match = re.search(
                                r"# Tests (\d+) points", cell.source
                            )
                            if match:
                                points = int(match.group(1))

                            # Замена на соответствующую ячейку из преподавательского файла
                            teacher_cell = tutor_notebook.cells[index]
                            cell.source = teacher_cell.source

                            try:
                                client.execute_cell(cell, index)
                                total_points += points
                            except CellExecutionError as ce:
                                logger.error(f"ОШИБКА: {ce}")
                                feedback.append(index)
        return (total_points, feedback)
