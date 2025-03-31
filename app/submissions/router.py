"""

- GET /api/solutions
  - Получение списка всех решений.
  - Параметры: фильтрация по заданию, статусу и студенту.

- GET /api/solutions/{id}
  - Получение конкретного решения по ID.

- POST /api/solutions
  - Создание нового решения.
  - Тело запроса: данные решения (ID задания, ID студента, сам файл решения).

- PUT /api/solutions/{id}
  - Обновление существующего решения.
  - Тело запроса: измененные данные решения.

- DELETE /api/solutions/{id}
  - Удаление решения по ID.


"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from nbclient import NotebookClient
from nbformat import read, NO_CONVERT
import nbformat
from nbclient.exceptions import CellExecutionError
import logging
import re
from app.assignment.service import AssignmentService
from app.auth.dependencies import get_current_user
from app.exceptions import IncorrectFormatAssignmentException, SyntaxException
from app.submissions.service import SubmissionsService
from app.submissions.utils import grade_notebook
from app.user.models import Users
from app.logger import configure_logging

logger = logging.getLogger(__name__)
configure_logging()


router = APIRouter(prefix="/submissions", tags=['Submissions'])


@router.post("/{assignment_id}", status_code=201)
async def add_submission(
    assignment_id: int,
    submission_file: UploadFile = File(...),
    current_user: Users = Depends(get_current_user)
):
    """Загрузка решения"""
    # TODO: добавить проверку даты
    assignment = await AssignmentService.find_one_or_none(id=assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Задание не найдено")

    # проверка формата файла
    filename = submission_file.filename
    if not filename.endswith(".ipynb"):
        raise IncorrectFormatAssignmentException

    notebook = read(submission_file.file, as_version=NO_CONVERT)
    client = NotebookClient(notebook)

    # проверка на синтаксические ошибки
    try:
        client.execute()
    except Exception as e:
        raise SyntaxException from e
    

    with open(f'app\\submissions\\student_submissions\\{current_user.id}_{assignment_id}.ipynb',
              'w', encoding='utf-8') as f:
        nbformat.write(notebook, f)

    await SubmissionsService.add(user_id=current_user.id,
                                 assignment_id=assignment_id,
                                 score=0,
                                 number_of_attempts=0)





@router.post("/{assignment_id}/check")
async def check_submission(
    assignment_id: int,
    current_user: Users = Depends(get_current_user)
):
    """Проверка решения"""
    # TODO: добавить проверку даты
    assignment = await AssignmentService.find_one_or_none(id=assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Задание не найдено")

    submission_service = await SubmissionsService.find_one_or_none(user_id=current_user.id,
                                                                   assignment_id=assignment_id)
    if not submission_service:
        raise HTTPException(status_code=404, detail="Решение не найдено")

    submission_path = f"app\\submissions\\student_submissions\\{current_user.id}_{assignment_id}.ipynb"
    submission = nbformat.read(submission_path, as_version=4)

    tutor_notebook_path = f"app\\assignment\\original_assignments\\{assignment_id}.ipynb"
    tutor_notebook = nbformat.read(tutor_notebook_path, as_version=4)

    client = NotebookClient(submission)

    # Выполняем каждую ячейку отдельно
    total_points = grade_notebook(client, submission, tutor_notebook)
    
    await SubmissionsService.update(model_id=submission_service.id,
                                    score=total_points,
                                    number_of_attempts=submission_service.number_of_attempts + 1)     
    return {"message": "ok",
            "score": total_points}
                

@router.post("/test/test")
async def test_submission(
    submission_file: UploadFile = File(...),
):
    """Возвращает блокнот"""
    notebook = read(submission_file.file, as_version=NO_CONVERT)
    return notebook