from datetime import date, time
from typing import List, Optional
import nbformat
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from app.assignment.schemas import AssignmentResponseSchema, AssignmentUpdateSchema
from app.assignment.utils import check_notebook, modify_notebook
from app.assignment.service import AssignmentService
from app.submissions.schemas import SubmissionsBaseSchema
from app.submissions.service import SubmissionsService
from app.auth.dependencies import check_tutor_role, get_current_user
from app.exceptions import IncorrectFormatAssignmentException
from app.user.models import Users


router = APIRouter(prefix="/assignments",
                   tags=['Assignments'],
                   dependencies=[Depends(check_tutor_role)])

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



@router.post("/", status_code=201)
async def add_assighment(
    name: str = Query(description="Название теста"),
    number_of_attempts: int = Query(description="Максимальное количество попыток", ge=1),
    start_date: date = Query(default=date.today(), description="Дата открытия теста"),
    start_time: time = Query(default=time, description="Время открытия теста"),
    due_date: date = Query(default=date.today(), description="Дата закрытия теста"),
    due_time: time = Query(default=time, description="Время закрытия теста"),
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
    assignment = await AssignmentService.add(name=name,
                                        start_date=start_date,
                                        start_time=start_time,
                                        due_date=due_date,
                                        due_time=due_time,
                                        number_of_attempts=number_of_attempts,
                                        user_id=current_user.id)

    with open(f'app\\assignment\\original_assignments\\{assignment}.ipynb',
              'w', encoding='utf-8') as f:
        nbformat.write(notebook, f)

    modified_notebook = modify_notebook(notebook) # редактируем файл
    with open(f'app\\assignment\\modified_assignments\\{assignment}.ipynb',
              'w', encoding='utf-8') as f:
        nbformat.write(modified_notebook, f)


@router.get("/", response_model=List[AssignmentResponseSchema])
async def get_assignments(current_user: Users = Depends(get_current_user)):
    """Получение списка всех заданий преподавателя"""
    return await AssignmentService.find_all(user_id=current_user.id)

@router.get("/{assignment_id}", response_model=Optional[AssignmentResponseSchema])
async def get_assignment(assignment_id: int, current_user: Users = Depends(get_current_user)):
    """Получение информации о задании по ID"""
    return await AssignmentService.find_one_or_none(id=assignment_id, user_id=current_user.id)

@router.put("/{assignment_id}")
async def update_assignment(assignment_id: int, updated_data: AssignmentUpdateSchema):
    """Обновление задания"""
    assignment = await AssignmentService.find_one_or_none(id=assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    await AssignmentService.update_assignment(assignment_id, updated_data)


@router.delete("/{assignment_id}", status_code=204)
async def delete_assignment(assignment_id: int, current_user: Users = Depends(get_current_user)):
    """Удаление задания по ID"""
    assignment = await AssignmentService.find_one_or_none(id=assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    await AssignmentService.delete(id=assignment_id, user_id=current_user.id)


@router.get("/{assignment_id}/stats", response_model=Optional[SubmissionsBaseSchema])
async def get_stats(assignment_id: int):
    assignment = await AssignmentService.find_one_or_none(id=assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    stats = await SubmissionsService.find_all(assignment_id=assignment_id)
    return stats