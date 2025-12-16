from datetime import date, datetime
import logging
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from app.assignment.router import (
    get_assignment,
    get_file_of_original_assignment,
    get_stats,
)
from app.assignment.schemas import AssignmentQueryParams, SortEnum
from app.assignment.services.dao_service import AssignmentDAO, DisciplinesDAO
from app.auth.dependencies_page import (
    check_student_role_page,
    check_tutor_role_page,
    get_current_user_page,
    refresh_token_page,
)
from app.exceptions import AssignmentNotFoundException
from app.logger import configure_logging
from app.submissions.services.service import (
    SubmissionFilesDAO,
    SubmissionsDAO,
)
from app.user.models import Users
from app.db import async_session_maker, get_db_session
from app.user.service import UsersDAO
logger = logging.getLogger("frontend")
configure_logging()
router = APIRouter(prefix="/pages", tags=["Фронт"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/auth/register", response_class=HTMLResponse)
async def register(request: Request):
    """Отображение страницы регистрации"""
    return templates.TemplateResponse(
        name="register.html",
        context={
            "request": request,
        },
    )


@router.get("/auth/login", response_class=HTMLResponse)
async def login(request: Request):
    """Отображение страницы авторизации"""
    return templates.TemplateResponse(
        name="login.html", context={"request": request}
    )


@router.get(
    "/tutor-home",
    response_model=None,
    response_class=HTMLResponse,
    dependencies=[Depends(refresh_token_page), Depends(check_tutor_role_page)],
)
async def tutor_home_page(
    request: Request,
    page: int = Query(1, ge=1),
    sort: str = Query("newest"),
    search: str | None = Query(None),
    discipline_id: str | None = Query(None),
    limit: int = Query(10, gt=0, le=50),
    current_user: Users = Depends(get_current_user_page),
    session: AsyncSession = Depends(get_db_session)
):
    if not isinstance(current_user, Users):
        return RedirectResponse(url="/pages/auth/login")

    offset = (page - 1) * limit

    # приводим discipline_id к int
    try:
        discipline_id_int = int(discipline_id)
    except (TypeError, ValueError):
        discipline_id_int = None

    order_by = "created_at"
    desc_order = sort.strip() == "newest"

    # Получаем записи напрямую из сервиса
    if discipline_id_int is not None:
        items = await AssignmentDAO.find_all(
            session=session,
            skip=offset,
            limit=limit,
            order_by=order_by,
            desc_order=desc_order,
            search=search,
            user_id=current_user.id,
            discipline_id=discipline_id_int
        )
        total = await AssignmentDAO.count(
            session=session,
            search=search,
            user_id=current_user.id,
            discipline_id=discipline_id_int
        )
    else:
        items = await AssignmentDAO.find_all(
            session=session,
            skip=offset,
            limit=limit,
            order_by=order_by,
            desc_order=desc_order,
            search=search,
            user_id=current_user.id,
        )
        total = await AssignmentDAO.count(
            session=session,
            search=search,
            user_id=current_user.id,
        )

    total_pages = (total + limit - 1) // limit
    disciplines = await DisciplinesDAO.find_all(session=session, teacher_id=current_user.id)

    return templates.TemplateResponse(
        "tutor-home.html",
        {
            "request": request,
            "assignments": items,
            "discipline_id": discipline_id_int,
            "disciplines": disciplines,
            "current_page": page,
            "total_pages": total_pages,
            "sort": sort,
            "search": search or "",
        },
    )


@router.get(
    "/assignments/{assignment_id}",
    response_class=HTMLResponse,
    dependencies=[Depends(refresh_token_page)],
)
async def assignment_page(
    request: Request,
    assignment_id: str,
    page: int = Query(1, ge=1),
    sort: str = Query("newest"),
    search: str | None = Query(None),
    discipline_id: str | None = Query(None),
    current_user: Users = Depends(get_current_user_page),
    session: AsyncSession = Depends(get_db_session)
):
    """Отображение страницы задания"""
    assignment = await AssignmentDAO.find_one_or_none(session=session, id=assignment_id)
    if not isinstance(current_user, Users):
        return RedirectResponse(url="/pages/auth/login")
    if current_user.role == "TUTOR":
        discipline = await DisciplinesDAO.find_one_or_none(
            session=session, id=assignment.discipline_id
        )
        return templates.TemplateResponse(
            "assignment.html",
            {
                "request": request,
                "assignment": assignment,
                "discipline": discipline,
                "page": page,
                "sort": sort,
                "search": search or "",
                "discipline_id": discipline_id,
            },
        )
    else:
        submission = await SubmissionsDAO.find_one_or_none(
            session=session, assignment_id=assignment_id, user_id=current_user.id
        )
        submission_file = None
        due = False
        if submission:
            if submission.number_of_attempts >= assignment.number_of_attempts:
                due = True
            submission_file = await SubmissionFilesDAO.find_one_or_none(
                session=session, submission_id=submission.id, assignment_id=assignment_id
            )
        if assignment.due_date < datetime.now().date():
            due = True
        if assignment.start_date > datetime.now().date():
            due = True
        if (
            assignment.due_date == datetime.now().date()
            and assignment.start_time < datetime.now().time()
        ):
            due = True

        return templates.TemplateResponse(
            "assignment-for-student.html",
            {
                "request": request,
                "assignment": assignment,
                "due": due,
                "submission": submission,
                "submission_file": submission_file,
                "page": page,
                "sort": sort,
                "search": search or "",
                "discipline_id": discipline_id,
            },
        )


@router.get(
    "/assignments/{assignment_id}/stats",
    response_class=HTMLResponse,
    dependencies=[Depends(refresh_token_page), Depends(check_tutor_role_page)],
)
async def stats(
    request: Request,
    assignment_id: str,
    # assignment=Depends(get_assignment),
    # stats=Depends(get_stats),
    page: int = Query(1, ge=1),
    sort: str = Query("newest"),
    limit: int = Query(3, gt=0, le=50),
    search: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session)
):
    assignment = await AssignmentDAO.find_one_or_none(session=session, id=assignment_id)
    discipline = await DisciplinesDAO.find_one_or_none(
        session=session, id=assignment.discipline_id
    )
    offset = (page - 1) * limit
    order_by = "created_at"
    desc_order = sort == SortEnum.newest

    if not assignment:
        raise AssignmentNotFoundException
    
    stats = await SubmissionsDAO.get_statistics(
        session=session,
        assignment_id=assignment_id,
        skip=offset,
        limit=limit,
        order_by=order_by,
        desc_order=desc_order,
        search=search,
    )
    logger.info(stats)

    return templates.TemplateResponse(
        "stats.html",
        {
            "request": request,
            "discipline": discipline,
            "assignment": assignment,
            "statistics": stats["submissions"],
            "avg_score": stats["average_score"],
            "current_page": page,
            "sort": sort.strip(),
            "search": search or "",
        },
    )


@router.get(
    "/assignments",
    response_class=HTMLResponse,
    dependencies=[Depends(refresh_token_page), Depends(check_tutor_role_page)],
)
async def create_assignment_page(
    request: Request, current_user: Users = Depends(get_current_user_page),
    session: AsyncSession = Depends(get_db_session)
):
    if not isinstance(current_user, Users):
        return RedirectResponse(url="/pages/auth/login")
    today = date.today().isoformat()
    disciplines = await DisciplinesDAO.find_all(session=session, teacher_id=current_user.id)
    return templates.TemplateResponse(
        "create.html",
        {"request": request, "today": today, "disciplines": disciplines},
    )

# TODO пофиксить обновление
@router.get(
    "/assignments/{assignment_id}/edit",
    response_class=HTMLResponse,
    dependencies=[Depends(refresh_token_page), Depends(check_tutor_role_page)],
)
async def update_assignment_page(
    request: Request,
    assignment_id: str,
    current_user: Users = Depends(get_current_user_page),
    session: AsyncSession = Depends(get_db_session)
):
    assignment = await AssignmentDAO.find_one_or_none(session=session, id=assignment_id)
    file = await get_file_of_original_assignment(assignment_id, session)
    disciplines = await DisciplinesDAO.find_all(session=session, teacher_id=current_user.id)
    return templates.TemplateResponse(
        "edit_assignment.html",
        {
            "request": request,
            "assignment": assignment,
            "file": file,
            "disciplines": disciplines,
        },
    )


### STUDENT ENDPOINTS


@router.get(
    "/student-home",
    response_model=None,
    response_class=HTMLResponse,
    dependencies=[
        Depends(refresh_token_page),
        Depends(check_student_role_page),
    ],
)
async def student_submissions_page(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(10, gt=0, le=50),
    current_user: Users = Depends(get_current_user_page),
    sort: str = Query("newest"),
    search: str | None = Query(None),
    discipline_id: str | None = Query(None),
    session: AsyncSession = Depends(get_db_session)
):
    """HTML-страница со списком решений студента"""
    if not isinstance(current_user, Users):
        return RedirectResponse(url="/pages/auth/login")
    
    # приводим discipline_id к int
    try:
        discipline_id_int = int(discipline_id)
    except (TypeError, ValueError):
        discipline_id_int = None

    skip = (page - 1) * limit
    order_by = "created_at"
    desc_order = sort.strip() == "newest"

    if discipline_id_int is not None:
        submissions = await SubmissionsDAO.find_all(
            session=session,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            order_by=order_by,
            desc_order=desc_order,
            search=search,
            discipline_id=discipline_id_int,
            )
        total = await SubmissionsDAO.count(
            session=session,
            user_id=current_user.id,
            search=search,
            discipline_id=discipline_id_int
            )
    else:
        submissions = await SubmissionsDAO.find_all(
            session=session,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            order_by=order_by,
            desc_order=desc_order,
            search=search,
            )
        total = await SubmissionsDAO.count(
            session=session,
            user_id=current_user.id,
            search=search,
            )

    disciplines = await DisciplinesDAO.find_for_student(
        session=session,
        student_id=current_user.id
    )

    total_pages = (total + limit - 1) // limit

    return templates.TemplateResponse(
        "student-home.html",
        {
            "request": request,
            "submissions": submissions,
            "current_page": page,
            "total_pages": total_pages,
            "sort": sort,
            "search": search or "",
            "disciplines": disciplines,
            "discipline_id": discipline_id_int,
        },
    )


@router.get(
    "/instructions",
    dependencies=[Depends(refresh_token_page)],
    response_class=HTMLResponse,
)
async def instructions(
    request: Request, current_user=Depends(get_current_user_page)
):
    if not isinstance(current_user, Users):
        return RedirectResponse(url="/pages/auth/login")
    role = current_user.role
    return templates.TemplateResponse(
        "instruction.html", {"request": request, "role": role}
    )


@router.get(
    "/profile",
    dependencies=[Depends(refresh_token_page)],
    response_class=HTMLResponse,
)
async def profile(
    request: Request, current_user=Depends(get_current_user_page),
    session: AsyncSession = Depends(get_db_session)
):
    if not isinstance(current_user, Users):
        return RedirectResponse(url="/pages/auth/login")
    role = current_user.role

    data = await UsersDAO.get_full_user_info(session, current_user.id)


    return templates.TemplateResponse(
        "profile.html", {"request": request,
                         "role": role,
                        "first_name": data["user"].first_name,
                        "last_name": data["user"].last_name,
                        "group": data["group"].name if data["group"] else None,
                        "disciplines": [
                            {"id": d.id, "name": d.name} for d in data["disciplines"]
                        ],}
    )


@router.get("/complete-profile")
async def complete(request: Request):
    return templates.TemplateResponse(
        "complete-profile.html", {"request": request}
    )
