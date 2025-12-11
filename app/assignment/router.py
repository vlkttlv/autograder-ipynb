import io
import csv
import logging
from datetime import date, datetime, time
from typing import Optional
from uuid import UUID
import nbformat
from openpyxl import Workbook
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Path,
    Query,
    Response,
    UploadFile,
)
from app.assignment.services.assignment_manager_service import (
    AssignmentManagerService,
)
from app.assignment.services.notebook_service import NotebookService
from app.user.models import Users
from app.user.router import refresh_token
from app.auth.dependencies import check_tutor_role, get_current_user
from app.assignment.services.dao_service import (
    AssignmentFileDAO,
    AssignmentDAO,
    DisciplinesDAO,
)
from app.submissions.services.service import (
    SubmissionFilesDAO,
    SubmissionsDAO,
)
from app.assignment.schemas import (
    AssignmentQueryParams,
    SortEnum,
    ExportMethod,
    StatsResponse,
    TypeOfAssignmentFile,
    AssignmentUpdateSchema,
    AssignmentListResponse,
    AssignmentResponseSchema,
)
from app.exceptions import (
    DisciplineNotFoundException,
    WgongDateException,
    DecodingIPYNBException,
    AssignmentNotFoundException,
    IncorrectFormatAssignmentException,
)
from app.dropbox.service import dropbox_service
from app.logger import configure_logging
from app.db import get_db_session

logger = logging.getLogger("assignments_service")
configure_logging()

router = APIRouter(prefix="/assignments", tags=["Assignments"])


@router.post(
    "/",
    status_code=201,
    dependencies=[Depends(refresh_token), Depends(check_tutor_role)],
)
async def add_assignment(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    number_of_attempts: int = Form(..., ge=1),
    discipline_id: int | None = Form(default=None),
    new_discipline_name: str | None = Form(default=None),
    start_date: date = Form(default=date.today()),
    start_time: time = Form(default=time),
    due_date: date = Form(default=date.today()),
    due_time: time = Form(default=time),
    assignment_file: UploadFile = File(...),
    current_user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Создание задания"""
    if (due_date < start_date) or (
        due_date == start_date and start_time > due_time
    ):
        raise WgongDateException
    if discipline_id:
        if await DisciplinesDAO.find_one_or_none(session=session, id=discipline_id, teacher_id=current_user.id):
            final_discipline_id = discipline_id
        else:
            raise DisciplineNotFoundException
    elif new_discipline_name:
        discipline = await DisciplinesDAO.find_one_or_none(
            session=session, name=new_discipline_name, teacher_id=current_user.id
        )
        if discipline:
            final_discipline_id = discipline.id
        else:
            new_discipline_id = await DisciplinesDAO.add(
                session=session, name=new_discipline_name, teacher_id=current_user.id
            )
            final_discipline_id = new_discipline_id
    else:
        raise HTTPException(
            status_code=400, detail="Не выбрана и не создана дисциплина"
        )

    content = await assignment_file.read()
    logger.info(f"Преподаватель {current_user.email} отправил задание")

    assignment_id, original_assignment, modified_assignment = await AssignmentManagerService.process_and_upload_assignment(
        session=session,
        content=content,
        discipline_id=final_discipline_id,
        name=name,
        number_of_attempts=number_of_attempts,
        start_date=start_date,
        start_time=start_time,
        due_date=due_date,
        due_time=due_time,
        user_id=current_user.id,
    )

    background_tasks.add_task(
        AssignmentManagerService.upload_to_dropbox_and_finalize,
        assignment_id,
        original_assignment,
        modified_assignment,
    )
    return {"status": "accepted", "assignment_id": assignment_id}


@router.get(
    "/",
    response_model=AssignmentListResponse,
    dependencies=[Depends(refresh_token), Depends(check_tutor_role)],
)
async def get_assignments(
    params: AssignmentQueryParams = Depends(),
    search: Optional[str] = Query(
        None, description="Поиск по названию задания"
    ),
    discipline_id: int | None = Query(None),
    current_user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Получение списка заданий с пагинацией, сортировкой и поиском"""
    offset = (params.page - 1) * params.limit
    order_by = "created_at"
    desc_order = params.sort == SortEnum.newest

    if discipline_id is not None:
        items = await AssignmentDAO.find_all(
            session=session,
            user_id=current_user.id,
            skip=offset,
            limit=params.limit,
            order_by=order_by,
            desc_order=desc_order,
            search=search,
            discipline_id=discipline_id,
        )
        total = await AssignmentDAO.count(
            session=session,
            user_id=current_user.id,
            search=search,
            discipline_id=discipline_id
        )
    else:
        items = await AssignmentDAO.find_all(
            session=session,
            user_id=current_user.id,
            skip=offset,
            limit=params.limit,
            order_by=order_by,
            desc_order=desc_order,
            search=search,
        )
        total = await AssignmentDAO.count(
            session=session,
            user_id=current_user.id,
            search=search
        )

    return {"assignments": items, "total": total}


@router.get(
    "/{assignment_id}",
    response_model=Optional[AssignmentResponseSchema],
    dependencies=[Depends(refresh_token), Depends(get_current_user)],
)
async def get_assignment(assignment_id: str, session: AsyncSession = Depends(get_db_session)):
    """Получение информации о задании по ID"""
    return await AssignmentDAO.find_one_or_none(session=session, id=assignment_id)


@router.get(
    "/{assignment_id}/file/original",
    dependencies=[Depends(refresh_token), Depends(get_current_user)],
)
async def get_file_of_original_assignment(assignment_id: str, session: AsyncSession = Depends(get_db_session)):
    """Скачивание оригинального файла задания с Google dropbox"""
    original_assignment = await AssignmentFileDAO.find_one_or_none(
        session=session, assignment_id=assignment_id, file_type=TypeOfAssignmentFile.ORIGINAL
    )
    if original_assignment is None:
        raise AssignmentNotFoundException

    content = dropbox_service.download_file(original_assignment.file_id)
    return Response(
        content=content,
        media_type="application/x-jupyter-notebook",
        headers={
            "Content-Disposition": f"attachment; filename={assignment_id}_orig.ipynb"
        },
    )


@router.get(
    "/{assignment_id}/file/modified",
    dependencies=[Depends(refresh_token), Depends(get_current_user)],
)
async def get_file_of_modified_assignment(assignment_id: str, session: AsyncSession = Depends(get_db_session)):
    """Скачивание модифицированного файла задания с Google dropbox"""
    modified_assignment = await AssignmentFileDAO.find_one_or_none(
        session=session, assignment_id=assignment_id, file_type=TypeOfAssignmentFile.MODIFIED
    )
    if modified_assignment is None:
        raise AssignmentNotFoundException

    content = dropbox_service.download_file(modified_assignment.file_id)
    return Response(
        content=content,
        media_type="application/x-jupyter-notebook",
        headers={
            "Content-Disposition": f"attachment; filename={assignment_id}_mod.ipynb"
        },
    )


# TODO
# эту фигню убрать куда нибудь
def remove_tz(t: time) -> time:
    return t.replace(tzinfo=None) if t.tzinfo else t


@router.patch(
    "/{assignment_id}",
    dependencies=[Depends(refresh_token), Depends(check_tutor_role)],
)
async def update_assignment(
    assignment_id: str, updated_data: AssignmentUpdateSchema = Body(...),
    current_user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Обновление задания"""
    assignment = await AssignmentDAO.find_one_or_none(session=session, id=assignment_id)
    if not assignment:
        raise AssignmentNotFoundException

    # проверка даты и времени
    start_date = updated_data.start_date or assignment.start_date
    due_date = updated_data.due_date or assignment.due_date

    start_time = remove_tz(updated_data.start_time or assignment.start_time)
    due_time = remove_tz(updated_data.due_time or assignment.due_time)

    # Преобразуем в datetime для удобного сравнения
    start_dt = datetime.combine(start_date, start_time)
    due_dt = datetime.combine(due_date, due_time)

    if due_dt <= start_dt:
        raise WgongDateException
    
    # Определяем дисциплину
    final_discipline_id = None

    if updated_data.discipline_id is not None:
        final_discipline_id = updated_data.discipline_id
    elif updated_data.new_discipline_name:
        discipline = await DisciplinesDAO.find_one_or_none(
            session=session, name=updated_data.new_discipline_name, teacher_id=current_user.id
        )
        if discipline:
            final_discipline_id = discipline.id
        else:
            final_discipline_id = await DisciplinesDAO.add(
                session=session,
                name=updated_data.new_discipline_name,
                teacher_id=current_user.id
            )
        updated_data.new_discipline_name = None

    # Составляем словарь для обновления
    update_fields = {k: v for k, v in updated_data.dict(exclude_unset=True).items() if v is not None}
    if final_discipline_id is not None:
        update_fields["discipline_id"] = final_discipline_id
    if updated_data.start_time is not None:
        update_fields["start_time"] = start_time
    if updated_data.due_time is not None:
        update_fields["due_time"] = due_time


    await AssignmentDAO.update(session=session, model_id=assignment_id, **update_fields)
    return {"message": "Данные обновлены", "updated": update_fields}


@router.patch(
    "/{assignment_id}/file",
    dependencies=[Depends(refresh_token), Depends(check_tutor_role)],
)
async def update_files_of_assignment(
    assignment_id: str,
    assignment_file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session)
):
    """Обновление файлов задания на Google dropbox"""
    new_assignment_id = await AssignmentManagerService.update_file(
        session=session, assignment_id=assignment_id, assignment_file=assignment_file
    )

    return {"status": "ok", "assignment_id": new_assignment_id}


@router.delete(
    "/{assignment_id}", status_code=204, dependencies=[Depends(refresh_token)]
)
async def delete_assignment(
    assignment_id: str,
    current_user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    """Удаление задания и файлов в Dropbox"""
    assignment = await AssignmentDAO.find_one_or_none(session=session, id=assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Задание не найдено")

    files = await AssignmentFileDAO.find_all(session=session, assignment_id=assignment_id)

    for f in files:
        if f.file_id:
            try:
                dropbox_service.delete_file(f.file_id)
            except Exception as e:
                logger.info(
                    f"Не удалось удалить файл с Dropbox: {f.file_id}, ошибка: {e}"
                )

    # Удаляем связанные сущности в БД
    await SubmissionFilesDAO.delete(session=session, assignment_id=assignment_id)
    await SubmissionsDAO.delete(session=session, assignment_id=assignment_id)
    await AssignmentFileDAO.delete(session=session, assignment_id=assignment_id)
    await AssignmentDAO.delete(session=session, id=assignment_id, user_id=current_user.id)


@router.get(
    "/{assignment_id}/stats",
    response_model=StatsResponse,
    dependencies=[Depends(refresh_token), Depends(check_tutor_role)],
)
async def get_stats(
    assignment_id: str,
    params: AssignmentQueryParams = Depends(),
    search: Optional[str] = Query(
        None, description="Поиск по имени студента"
    ),
    session: AsyncSession = Depends(get_db_session),
):
    """Получение статистики по заданию"""
    offset = (params.page - 1) * params.limit
    order_by = "created_at"
    desc_order = params.sort == SortEnum.newest

    assignment = await AssignmentDAO.find_one_or_none(session=session, id=assignment_id)
    if not assignment:
        raise AssignmentNotFoundException
    total = await SubmissionsDAO.count(session=session, assignment_id=assignment_id)
    stats = await SubmissionsDAO.get_statistics(
        session=session,
        assignment_id=assignment_id,
        skip=offset,
        limit=params.limit,
        order_by=order_by,
        desc_order=desc_order,
        search=search,
    )
    return {
        "submissions": stats["submissions"],
        "average_score": stats["average_score"],
        "total": total,
    }


@router.get(
    "/{assignment_id}/stats/download",
    dependencies=[Depends(refresh_token), Depends(check_tutor_role)],
)
async def get_stats_to_csv(assignment_id: str, method: ExportMethod):
    """Выгрузка статистики в csv/excel"""
    stats = await get_stats(assignment_id)
    stat = stats["submissions"]
    headers = ["Студент", "Почта", "Количество попыток", "Баллы"]

    if method == ExportMethod.CSV:
        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")
        writer.writerow(headers)
        for student in stat:
            writer.writerow(
                [
                    student.user.last_name + " " + student.user.first_name,
                    student.user.email,
                    student.number_of_attempts,
                    student.score,
                ]
            )
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=stats_{assignment_id}.csv"
            },
        )

    elif method == ExportMethod.XLSX:
        output = io.BytesIO()
        wb = Workbook()
        ws = wb.active
        ws.title = "Статистика"
        ws.append(headers)
        for student in stat:
            ws.append(
                [
                    student.user.last_name + " " + student.user.first_name,
                    student.user.email,
                    student.number_of_attempts,
                    student.score,
                ]
            )
        wb.save(output)
        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=stats_{assignment_id}.xlsx"
            },
        )


@router.post("/process")
async def process(assignment_file: UploadFile = File(...)):
    """
    Проверка и редактирование файла без сохранения
    Возвращает отредактированный файл
    """
    filename = assignment_file.filename
    if not filename.endswith(".ipynb"):
        raise IncorrectFormatAssignmentException
    content = await assignment_file.read()
    try:
        notebook = nbformat.reads(content.decode("utf-8"), as_version=4)
    except Exception as e:
        raise DecodingIPYNBException from e
    NotebookService.check_notebook(
        notebook
    )  # проверка, есть ли нужные блоки в файле
    modified_notebook = NotebookService.modify_notebook(
        notebook
    )  # редактируем файл
    return modified_notebook
