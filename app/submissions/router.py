from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pathlib import Path
from nbclient import NotebookClient
from nbformat import read, NO_CONVERT
import nbformat
import logging
from app.auth.dependencies import check_student_role, get_current_user
from app.exceptions import IncorrectFormatAssignmentException, SolutionNotFoundException, SyntaxException
from app.submissions.service import SubmissionsService
from app.submissions.utils import (check_date_and_attempts_submission,
                                   check_date_submission,
                                   grade_notebook)
from app.user.models import Users
from app.logger import configure_logging

logger = logging.getLogger(__name__)
configure_logging()


router = APIRouter(prefix="/submissions", tags=['Submissions'])


@router.post("/{assignment_id}", status_code=201, dependencies=[Depends(check_student_role)])
async def add_submission(
    assignment_id: int,
    submission_file: UploadFile = File(...),
    current_user: Users = Depends(get_current_user)
):
    """Загрузка решения"""

    await check_date_submission(assignment_id)

    # проверка формата файла
    filename = submission_file.filename
    if not filename.endswith(".ipynb"):
        raise IncorrectFormatAssignmentException

    notebook = read(submission_file.file, as_version=NO_CONVERT)
    client = NotebookClient(notebook)

    try: # проверка на синтаксические ошибки
        client.execute()
    except Exception as e:
        raise SyntaxException from e


    with open(f'app\\submissions\\student_submissions\\{current_user.id}_{assignment_id}.ipynb',
              'w', encoding='utf-8') as f:
        nbformat.write(notebook, f)
    res = await SubmissionsService.find_one_or_none(user_id=current_user.id, assignment_id=assignment_id)
    if res is None:
        await SubmissionsService.add(user_id=current_user.id,
                                    assignment_id=assignment_id,
                                    score=0,
                                    number_of_attempts=0)

    logger.info("Пользователь %s загрузил решение для задания %s", current_user.email, assignment_id)


@router.get("/{assignment_id}/download",
            dependencies=[Depends(check_student_role)])
async def download_assignment(
    assignment_id: int
):
    """Загрузка задания"""

    await check_date_submission(assignment_id)
    file_path = Path(f"app\\assignment\\modified_assignments\\{assignment_id}.ipynb")
    return FileResponse(file_path,
                        media_type='application/x-jupyter-notebook',
                        filename=f"{assignment_id}.ipynb")

                
@router.post("/{assignment_id}/check", dependencies=[Depends(check_student_role)])
async def check_submission(
    assignment_id: int,
    current_user: Users = Depends(get_current_user)
):
    """Проверка решения"""

    submission_service = await check_date_and_attempts_submission(assignment_id, current_user)
    
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

    logger.info("Пользователь %s проверил решение задания %s", current_user.email, assignment_id)   

    return {"message": "ok",
            "score": total_points}

@router.get("/", dependencies=[Depends(check_student_role)])
async def get_submissions(current_user: Users = Depends(get_current_user)):
    """Получение списка всех решений"""
    return await SubmissionsService.find_all(user_id=current_user.id)


@router.get("/{submission_id}", dependencies=[Depends(check_student_role)])
async def get_submission_by_id(submission_id: int, current_user: Users = Depends(get_current_user)):
    """Получение конкретного решения по ID"""
    submission = await SubmissionsService.find_one_or_none(id=submission_id, user_id=current_user.id)
    if not submission:
        raise SolutionNotFoundException
    return submission

@router.get("/{submission_id}/get", dependencies=[Depends(get_current_user)])
async def download_submission(submission_id: int, user_id: int):
    """Скачивание файла с решением"""

    # Проверяем наличие решения в базе
    submission = await SubmissionsService.find_one_or_none(id=submission_id, user_id=user_id)
    if not submission:
        raise SolutionNotFoundException

    # Формируем путь к файлу
    file_path = Path(f"app/submissions/student_submissions/{user_id}_{submission.assignment_id}.ipynb")

    # Проверяем, что файл существует
    if not file_path.exists():
        raise SolutionNotFoundException

    return FileResponse(
        path=file_path,
        media_type='application/x-jupyter-notebook',
        filename=f"{submission.assignment_id}_submission.ipynb"
    )


@router.delete("/{submission_id}", dependencies=[Depends(check_student_role)])
async def delete_submission(submission_id: int, current_user: Users = Depends(get_current_user)):
    """Удаление решения по ID"""
    submission = await SubmissionsService.find_one_or_none(id=submission_id, user_id=current_user.id)
    if not submission:
        raise SolutionNotFoundException
    await SubmissionsService.delete(id=submission_id, user_id=current_user.id)
    return {"message": "Решение удалено"}


@router.post("/test/test", summary="Returns notebook")
async def test_submission(
    submission_file: UploadFile = File(...),
):
    """Возвращает блокнот"""
    notebook = read(submission_file.file, as_version=NO_CONVERT)
    return notebook