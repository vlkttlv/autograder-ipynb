from datetime import datetime
import re
from nbclient.exceptions import CellExecutionError

from app.assignment.service import AssignmentService
from app.exceptions import AssignmentNotFoundException, DeadlineException, EndedAttemptsException, SolutionNotFoundException
from app.submissions.service import SubmissionsService


def grade_notebook(client, submission, tutor_notebook):
    total_points = 0
    # Выполняем каждую ячейку отдельно
    with client.setup_kernel() as kernel:
        for index, cell in enumerate(submission.cells):
            if cell.cell_type == 'code':  # Проверяем, что это кодовая ячейка
                try:
                    client.execute_cell(cell, cell_index=index, store_history=True)
                except CellExecutionError:
                    pass
                if cell.cell_type == 'code':
                    if "# Tests " in cell.source and " points." in cell.source:
                        points = 0
                        match = re.search(r"# Tests (\d+) points", cell.source)
                        if match:
                            points = int(match.group(1))

                        # Замена на соответствующую ячейку из преподавательского файла
                        teacher_cell = tutor_notebook.cells[index]
                        cell.source = teacher_cell.source
                        
                        try:
                            client.execute_cell(cell, index)
                            total_points += points
                        except CellExecutionError as ce:
                            pass
    return total_points


async def check_date_and_attempts_submission(assignment_id, current_user):
    now_datetime = datetime.now()
    assignment = await AssignmentService.find_one_or_none(id=assignment_id)

    if not assignment:
        raise AssignmentNotFoundException

    if assignment.due_date < now_datetime.date() or assignment.start_date > now_datetime.date():
        raise DeadlineException

    submission_service = await SubmissionsService.find_one_or_none(user_id=current_user.id,
                                                                   assignment_id=assignment_id)
    if not submission_service:
        raise SolutionNotFoundException
    
    if submission_service.number_of_attempts == assignment.number_of_attempts:
        raise EndedAttemptsException
    
    return submission_service


async def check_date_submission(assignment_id):
    now_datetime = datetime.now()
    assignment = await AssignmentService.find_one_or_none(id=assignment_id)

    if not assignment:
        raise AssignmentNotFoundException

    if assignment.due_date < now_datetime.date() or assignment.start_date > now_datetime.date():
        raise DeadlineException