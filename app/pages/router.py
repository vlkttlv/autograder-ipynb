from datetime import date, datetime
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.assignment.models import Assignments
from app.assignment.schemas import SortEnum
from app.assignment.router import (
    get_assignment,
    get_assignments,
    get_file_of_original_assignment,
    get_stats,
)
from app.assignment.services.dao_service import DisciplinesService
from app.auth.dependencies_page import (
    check_student_role_page,
    check_tutor_role_page,
    get_current_user_page,
    refresh_token_page,
)
from app.submissions.services.service import (
    SubmissionFilesService,
    SubmissionsService,
)
from app.user.models import Users
from app.db import async_session_maker

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
    response_class=HTMLResponse,
    dependencies=[Depends(refresh_token_page), Depends(check_tutor_role_page)],
)
async def tutor_home_page(
    request: Request,
    page: int = Query(1, ge=1),
    sort: str = Query("newest"),
    search: str | None = Query(None, description="Поисковый запрос"),
    discipline_id: str | None = Query(None),
    current_user: Users = Depends(get_current_user_page),
):
    """Страница списка заданий преподавателя с поиском, сортировкой и пагинацией."""
    if not isinstance(current_user, Users):
        return RedirectResponse(url="/pages/auth/login")
    limit = 3
    skip = (page - 1) * limit

    # пустая строка или None -> None, иначе пробуем int
    if discipline_id:
        try:
            discipline_id = int(discipline_id)
        except ValueError:
            discipline_id = None
    else:
        discipline_id = None

    # Вызов API напрямую с актуальными параметрами
    api_response = await get_assignments(
        current_user=current_user,
        skip=skip,
        limit=limit,
        sort=SortEnum(sort.strip()),  # убираем пробелы,
        search=search or "",
        discipline_id=discipline_id,
    )

    assignments = api_response["assignments"]
    
    total = api_response["total"]
    total_pages = (total + limit - 1) // limit

    disciplines = await DisciplinesService.find_all(
        teacher_id=current_user.id
    )

    return templates.TemplateResponse(
        "tutor-home.html",
        {
            "request": request,
            "assignments": assignments,
            "discipline_id": discipline_id,
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
    discipline_id: str | None = Query(None),
    sort: str = Query("newest"),
    search: str | None = Query(None),
    current_user: Users = Depends(get_current_user_page),
):
    """Отображение страницы задания"""
    assignment = await get_assignment(assignment_id)
    if not isinstance(current_user, Users):
        return RedirectResponse(url="/pages/auth/login")
    if current_user.role == "TUTOR":
        discipline = await DisciplinesService.find_one_or_none(
            id=assignment.discipline_id
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
            },
        )
    else:
        submission = await SubmissionsService.find_one_or_none(
            assignment_id=assignment_id, user_id=current_user.id
        )
        submission_file = None
        due = False
        if submission:
            if submission.number_of_attempts >= assignment.number_of_attempts:
                due = True
            submission_file = await SubmissionFilesService.find_one_or_none(
                submission_id=submission.id, assignment_id=assignment_id
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
    stats=Depends(get_stats),
    page: int = Query(1, ge=1),
    sort: str = Query("newest"),
    search: str | None = Query(None),
):
    assignment = await get_assignment(assignment_id)
    discipline = await DisciplinesService.find_one_or_none(
        id=assignment.discipline_id
    )
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
async def create_assignment_page(request: Request, current_user: Users = Depends(get_current_user_page)):
    if not isinstance(current_user, Users):
        return RedirectResponse(url="/pages/auth/login")
    today = date.today().isoformat()
    disciplines = await DisciplinesService.find_all(
        teacher_id=current_user.id
    )
    return templates.TemplateResponse(
        "create.html", {"request": request, "today": today, "disciplines": disciplines}
    )


@router.get(
    "/assignments/{assignment_id}/edit",
    response_class=HTMLResponse,
    dependencies=[Depends(refresh_token_page), Depends(check_tutor_role_page)],
)
async def update_assignment_page(
    request: Request,
    assignment_id: str,
    # assignment=Depends(get_assignment),
    # file=Depends(get_file_of_original_assignment),
):
    assignment = await get_assignment(assignment_id)
    file = await get_file_of_original_assignment(assignment_id)
    return templates.TemplateResponse(
        "edit_assignment.html",
        {
            "request": request,
            "assignment": assignment,
            "file": file,
        },
    )


### STUDENT ENDPOINTS


@router.get(
    "/student-home",
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
):
    """HTML-страница со списком решений студента"""
    if not isinstance(current_user, Users):
        return RedirectResponse(url="/pages/auth/login")
    skip = (page - 1) * limit
    total = await SubmissionsService.count(user_id=current_user.id)
    submissions = await SubmissionsService.find_all(
        current_user.id,
        skip,
        limit,
    )

    total_pages = (total + limit - 1) // limit

    return templates.TemplateResponse(
        "student-home.html",
        {
            "request": request,
            "submissions": submissions,
            "current_page": page,
            "total_pages": total_pages,
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
    if current_user is not Users:
        return RedirectResponse(url="/pages/auth/login")
    role = current_user.role
    return templates.TemplateResponse(
        "instruction.html", {"request": request, "role": role}
    )


@router.get("/complete-profile")
async def complete(request: Request):
    return templates.TemplateResponse(
        "complete-profile.html", {"request": request}
    )
