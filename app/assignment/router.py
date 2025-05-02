import nbformat
from datetime import date, time
from typing import List, Optional
from nbclient import NotebookClient
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from app.assignment.schemas import AssignmentResponseSchema, AssignmentUpdateSchema, TypeOfAssignmentFile
from app.assignment.utils import check_notebook, get_total_points_from_notebook, modify_notebook
from app.assignment.service import AssignmentFileService, AssignmentService
from app.submissions.service import SubmissionFilesService, SubmissionsService
from app.auth.dependencies import check_tutor_role, get_current_user
from app.exceptions import (AssignmentNotFoundException,
                            DecodingIPYNBException,
                            IncorrectFormatAssignmentException,
                            WgongDateException)
from app.user.models import Users

router = APIRouter(prefix="/assignments", tags=['Assignments'])


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
    if (due_date < start_date) or (due_date == start_date and start_time > due_time):
        raise WgongDateException

    filename = assignment_file.filename
    if not filename.endswith(".ipynb"):
        raise IncorrectFormatAssignmentException

    content = await assignment_file.read()

    try:
        notebook = nbformat.reads(content.decode('utf-8'), as_version=4)
    except Exception as e:
        raise DecodingIPYNBException from e

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

    original_assignment = nbformat.writes(notebook).encode("utf-8")
    await AssignmentFileService.add(assignment_id=assignment,
                                    file_type=TypeOfAssignmentFile.ORIGINAL,
                                    content=original_assignment)

    modified_notebook = modify_notebook(notebook) # редактируем файл
    modified_assignment = nbformat.writes(modified_notebook).encode("utf-8")
    await AssignmentFileService.add(assignment_id=assignment,
                                file_type=TypeOfAssignmentFile.MODIFIED,
                                content=modified_assignment)
    return {"status": "ok",
            "assignment": assignment}


@router.get("/", response_model=List[AssignmentResponseSchema], dependencies=[Depends(check_tutor_role)])
async def get_assignments(current_user: Users = Depends(get_current_user)):
    """Получение списка всех заданий преподавателя"""
    return await AssignmentService.find_all(user_id=current_user.id)


@router.get("/{assignment_id}",
            response_model=Optional[AssignmentResponseSchema],
            dependencies=[Depends(get_current_user)])
async def get_assignment(assignment_id: str):
    """Получение информации о задании по ID"""
    return await AssignmentService.find_one_or_none(id=assignment_id)


@router.get("/{assignment_id}/file/original")
async def get_file_of_original_assignment(assignment_id: str):
    """Получение файла оригинального задания"""
    original_assignment = await AssignmentFileService.find_one_or_none(
                                                    assignment_id=assignment_id,
                                                    file_type=TypeOfAssignmentFile.ORIGINAL)
    if original_assignment is None:
        raise AssignmentNotFoundException
    return Response(content=original_assignment.content,
                    media_type='application/x-jupyter-notebook',
                    headers={"Content-Disposition": f"attachment; filename={assignment_id}_orig.ipynb"})


@router.get("/{assignment_id}/file/modified")
async def get_file_of_modified_assignment(assignment_id: str):
    """Получение измененного задания"""
    modified_assignment = await AssignmentFileService.find_one_or_none(
                                                    assignment_id=assignment_id,
                                                    file_type=TypeOfAssignmentFile.MODIFIED)
    if modified_assignment is None:
        raise AssignmentNotFoundException
    return Response(content=modified_assignment.content,
                    media_type='application/x-jupyter-notebook',
                    headers={"Content-Disposition": f"attachment; filename={assignment_id}_mod.ipynb"})

@router.patch("/{assignment_id}")
async def update_assignment(assignment_id: str,
                            updated_data: AssignmentUpdateSchema):
    """Обновление задания"""
    assignment = await AssignmentService.find_one_or_none(id=assignment_id)
    if not assignment:
        raise AssignmentNotFoundException
    await AssignmentService.update_assignment(assignment_id, updated_data)

@router.patch("/{assignment_id}/file")
async def update_files_of_assignment(assignment_id: str,
                                     assignment_file: UploadFile = File(...),):
    """Обновление файлов задания"""
    filename = assignment_file.filename
    if not filename.endswith(".ipynb"):
        raise IncorrectFormatAssignmentException
    content = await assignment_file.read()
    try:
        notebook = nbformat.reads(content.decode('utf-8'), as_version=4)
    except Exception as e:
        raise DecodingIPYNBException from e

    check_notebook(notebook) # проверка, есть ли нужные блоки в файле

    original_assignment = nbformat.writes(notebook).encode("utf-8")
    await AssignmentFileService.add(assignment_id=assignment_id,
                                    file_type=TypeOfAssignmentFile.ORIGINAL,
                                    content=original_assignment)

    modified_notebook = modify_notebook(notebook) # редактируем файл
    modified_assignment = nbformat.writes(modified_notebook).encode("utf-8")
    await AssignmentFileService.add(assignment_id=assignment_id,
                                file_type=TypeOfAssignmentFile.MODIFIED,
                                content=modified_assignment)
    
    client = NotebookClient(notebook)
    grade = get_total_points_from_notebook(client, notebook)
    assignment = await AssignmentService.update(model_id=assignment_id,
                                                           grade=grade)

@router.delete("/{assignment_id}", status_code=204)
async def delete_assignment(assignment_id: str, current_user: Users = Depends(get_current_user)):
    """Удаление задания по ID"""
    assignment = await AssignmentService.find_one_or_none(id=assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Задание не найдено")
    await SubmissionFilesService.delete(assignment_id=assignment_id)
    await SubmissionsService.delete(assignment_id=assignment_id)
    await AssignmentFileService.delete(assignment_id=assignment_id)
    await AssignmentService.delete(id=assignment_id, user_id=current_user.id)


@router.get("/{assignment_id}/stats")
async def get_stats(assignment_id: str):
    """Получение статистики по заданию"""
    assignment = await AssignmentService.find_one_or_none(id=assignment_id)
    if not assignment:
        raise AssignmentNotFoundException
    stats = await SubmissionsService.get_statistics(assignment_id=assignment_id)
    return stats

@router.post("/process")
async def process(assignment_file: UploadFile = File(...)):
    """Проверка и редактирование файла без сохранения.
    Возвращает отредактированный файл"""
    filename = assignment_file.filename
    if not filename.endswith(".ipynb"):
        raise IncorrectFormatAssignmentException
    content = await assignment_file.read()
    try:
        notebook = nbformat.reads(content.decode('utf-8'), as_version=4)
    except Exception as e:
        raise DecodingIPYNBException from e
    check_notebook(notebook) # проверка, есть ли нужные блоки в файле
    modified_notebook = modify_notebook(notebook) # редактируем файл
    return modified_notebook
