import os
from datetime import date, time
from pathlib import Path
from typing import List, Optional
from fastapi.responses import FileResponse
from nbclient import NotebookClient
import nbformat
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from app.assignment.schemas import AssignmentResponseSchema, AssignmentUpdateSchema
from app.assignment.utils import check_notebook, get_total_points_from_notebook, modify_notebook
from app.assignment.service import AssignmentService
from app.submissions.service import SubmissionsService
from app.auth.dependencies import check_tutor_role, get_current_user
from app.exceptions import IncorrectFormatAssignmentException
from app.user.models import Users

router = APIRouter(prefix="/assignments",
                   tags=['Assignments'])


ORIGINAL_ASSIGNMENTS_PATH = os.getenv("ASSIGNMENT_ORIGINAL_DIR", "app\\assignment\\original_assignments")
MODIFIED_ASSIGNMENTS_PATH = os.getenv("ASSIGNMENT_MODIFIED_DIR", "app\\assignment\\modified_assignments")

@router.post("/test")
async def test(assignment_file: UploadFile = File(...)):
    """Возвращает отредаченный файл ipynb"""
    filename = assignment_file.filename
    if not filename.endswith(".ipynb"):
        raise IncorrectFormatAssignmentException

    content = await assignment_file.read()

    try:
        notebook = nbformat.reads(content.decode('utf-8'), as_version=4)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Ошибка при декодировании файла .ipynb") from e

    check_notebook(notebook) # проверка, есть ли нужные блоки в файле
    modified_notebook = modify_notebook(notebook) # редактируем файл
    return modified_notebook



@router.post("/", status_code=201, dependencies=[Depends(check_tutor_role)])
async def add_assighment(
    name: str = Form(description="Название теста"),
    number_of_attempts: int = Form(description="Максимальное количество попыток", ge=1),
    start_date: date = Form(default=date.today(), description="Дата открытия теста"),
    start_time: time = Form(default=time, description="Время открытия теста"),
    due_date: date = Form(default=date.today(), description="Дата закрытия теста"),
    due_time: time = Form(default=time, description="Время закрытия теста"),
    assignment_file: UploadFile = File(...),
    current_user: Users = Depends(get_current_user)
):
    """Загрузка задания"""
    filename = assignment_file.filename
    if not filename.endswith(".ipynb"):
        raise IncorrectFormatAssignmentException

    content = await assignment_file.read()

    try:
        notebook = nbformat.reads(content.decode('utf-8'), as_version=4)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Ошибка при декодировании файла .ipynb") from e

    check_notebook(notebook) # проверка, есть ли нужные блоки в файле
    client = NotebookClient(notebook)
    grade = get_total_points_from_notebook(client, notebook)
    assignment = await AssignmentService.add(name=name,
                                        start_date=start_date,
                                        start_time=start_time,
                                        due_date=due_date,
                                        due_time=due_time,
                                        number_of_attempts=number_of_attempts,
                                        grade=grade,
                                        user_id=current_user.id)

    with open(os.path.join(ORIGINAL_ASSIGNMENTS_PATH, f"{assignment}.ipynb"),
              'w', encoding='utf-8') as f:
        nbformat.write(notebook, f)

    modified_notebook = modify_notebook(notebook) # редактируем файл
    with open(os.path.join(MODIFIED_ASSIGNMENTS_PATH, f"{assignment}.ipynb"),
              'w', encoding='utf-8') as f:
        nbformat.write(modified_notebook, f)


@router.get("/", response_model=List[AssignmentResponseSchema], dependencies=[Depends(check_tutor_role)])
async def get_assignments(current_user: Users = Depends(get_current_user)):
    """Получение списка всех заданий преподавателя"""
    return await AssignmentService.find_all(user_id=current_user.id)

@router.get("/{assignment_id}", response_model=Optional[AssignmentResponseSchema])
async def get_assignment(assignment_id: int, current_user: Users = Depends(get_current_user)):
    """Получение информации о задании по ID"""
    return await AssignmentService.find_one_or_none(id=assignment_id)


@router.get("/original/{assignment_id}")
async def get_original_assignment(assignment_id: int):
    """Получение оригинального задания"""
    file_path = Path(f"app\\assignment\\original_assignments\\{assignment_id}.ipynb")
    return FileResponse(file_path,
                        media_type='application/x-jupyter-notebook',
                        filename=f"{assignment_id}.ipynb")


@router.get("/modified/{assignment_id}")
async def get_modified_assignment(assignment_id: int):
    """Получение оригинального задания"""
    file_path = Path(f"app\\assignment\\modified_assignments\\{assignment_id}.ipynb")
    return FileResponse(file_path,
                        media_type='application/x-jupyter-notebook',
                        filename=f"{assignment_id}.ipynb")


@router.patch("/{assignment_id}")
async def update_assignment(assignment_id: int, updated_data: AssignmentUpdateSchema):
    """Обновление задания"""
    assignment = await AssignmentService.find_one_or_none(id=assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    await AssignmentService.update_assignment(assignment_id, updated_data)

@router.post("/{assignment_id}/file/update")
async def update_file_assignment(assignment_id: int,
                                 assignment_file: UploadFile = File(...),):
    
    filename = assignment_file.filename
    if not filename.endswith(".ipynb"):
        raise IncorrectFormatAssignmentException

    content = await assignment_file.read()

    try:
        notebook = nbformat.reads(content.decode('utf-8'), as_version=4)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Ошибка при декодировании файла .ipynb") from e

    check_notebook(notebook) # проверка, есть ли нужные блоки в файле

    with open(os.path.join(ORIGINAL_ASSIGNMENTS_PATH, f"{assignment_id}.ipynb"),
              'w', encoding='utf-8') as f:
        nbformat.write(notebook, f)

    modified_notebook = modify_notebook(notebook) # редактируем файл
    with open(os.path.join(MODIFIED_ASSIGNMENTS_PATH, f"{assignment_id}.ipynb"),
              'w', encoding='utf-8') as f:
        nbformat.write(modified_notebook, f)

@router.delete("/{assignment_id}", status_code=204)
async def delete_assignment(assignment_id: int, current_user: Users = Depends(get_current_user)):
    """Удаление задания по ID"""
    assignment = await AssignmentService.find_one_or_none(id=assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    await AssignmentService.delete(id=assignment_id, user_id=current_user.id)
    os.remove(f"app\\assignment\\modified_assignments\\{assignment_id}.ipynb")
    os.remove(f"app\\assignment\\original_assignments\\{assignment_id}.ipynb")


@router.get("/{assignment_id}/stats")
async def get_stats(assignment_id: int):
    assignment = await AssignmentService.find_one_or_none(id=assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    stats = await SubmissionsService.get_statistics(assignment_id=assignment_id)
    return stats

