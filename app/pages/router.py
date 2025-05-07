from datetime import date, datetime
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.assignment.router import get_assignment, get_file_of_original_assignment, get_stats
from app.assignment.service import AssignmentService
from app.auth.dependencies import check_student_role, check_tutor_role, get_current_user, get_role
from app.submissions.service import SubmissionFilesService, SubmissionsService
from app.user.models import Users

router = APIRouter(
    prefix="/pages",
    tags=["Фронт"]
)

templates = Jinja2Templates(directory="app/templates")

@router.get("/base")
async def home(request: Request, current_role = Depends(get_role)):
    tutor_role = False
    if current_role == 'TUTOR':
        tutor_role = True
    return templates.TemplateResponse("base.html",
                                      {"request": request,
                                       "role": tutor_role,
                                       "show_home_link": True })


@router.get("/auth/register", response_class=HTMLResponse)
async def register(request: Request):
    """Отображение страницы регистрации"""
    return templates.TemplateResponse(name="register.html", context={"request": request, })


@router.get("/auth/login", response_class=HTMLResponse)
async def login(request: Request):
    """Отображение страницы авторизации"""
    return templates.TemplateResponse(name="login.html", context={"request": request})


@router.get("/tutor-home",
            response_class=HTMLResponse,
            dependencies=[Depends(check_tutor_role)])
async def tutor_home(request: Request, current_user: Users = Depends(get_current_user)):
    """Отображение главной страницы преподавателя"""
    assignments = await AssignmentService.find_all(user_id=current_user.id)
    return templates.TemplateResponse(
        name="tutor-home.html",
        context={"request": request,
                 "assignments": assignments,
                 "show_home_link": False }
    )


@router.get("/assignments/{assignment_id}",
            response_class=HTMLResponse)
async def assignment_page(request: Request,
                          assignment_id: str,
                          assignment = Depends(get_assignment),
                          current_user: Users = Depends(get_current_user)):
    """Отображение страницы задания"""
    if current_user.role == 'TUTOR':
        return templates.TemplateResponse("assignment.html", {
            "request": request,
            "assignment": assignment,
            "show_home_link": True 
        })
    else:
        submission = await SubmissionsService.find_one_or_none(assignment_id=assignment_id,
                                                               user_id=current_user.id)
        submission_file = None
        due = False
        if submission:
            if submission.number_of_attempts >= assignment.number_of_attempts:
                due = True
            submission_file = await SubmissionFilesService.find_one_or_none(submission_id=submission.id,
                                                                            assignment_id=assignment_id)
        if assignment.due_date < datetime.now().date():
            due = True
        if assignment.start_date > datetime.now().date():
            due = True
        if assignment.due_date == datetime.now().date() and assignment.start_time < datetime.now().time():
            due = True
        return templates.TemplateResponse("assignment-for-student.html", {
            "request": request,
            "assignment": assignment,
            "due": due,
            "submission": submission,
            "submission_file": submission_file,
            "show_home_link": True 
        })



@router.get("/assignments/{assignment_id}/stats",
            response_class=HTMLResponse,
            dependencies=[Depends(check_tutor_role)])
async def stats(request: Request,
                assignment = Depends(get_assignment),
                statistics = Depends(get_stats)):
    return templates.TemplateResponse(
        "stats.html",
        {
            "request": request,
            "assignment": assignment,
            "statistics": statistics,
            "show_home_link": True
        }
    )


@router.get("/assignments",
            response_class=HTMLResponse,
            dependencies=[Depends(check_tutor_role)])
async def create_assignment_page(request: Request):
    today = date.today().isoformat()
    return templates.TemplateResponse("create.html", {"request": request, "today": today, "show_home_link": True})


@router.get("/assignments/{assignment_id}/edit",
            response_class=HTMLResponse,
            dependencies=[Depends(check_tutor_role)])
async def update_assignment_page(request: Request,
                                 assignment = Depends(get_assignment),
                                 file  = Depends(get_file_of_original_assignment)):
    return templates.TemplateResponse("edit_assignment.html",
                                      {"request": request,
                                       "assignment": assignment,
                                       "file": file,
                                       "show_home_link": True })


### STUDENT ENDPOINTS


@router.get("/student-home",
            response_class=HTMLResponse,
            dependencies=[Depends(check_student_role)])
async def student_home(request: Request, current_user: Users = Depends(get_current_user)):
    submissions = await SubmissionsService.find_all(user_id=current_user.id)
    return templates.TemplateResponse(
        name="student-home.html",
        context={"request": request, "submissions": submissions, "show_home_link": False }
    )


@router.get("/instructions", response_class=HTMLResponse)
async def instructions(request: Request):
    return templates.TemplateResponse("instruction.html", {"request": request, "show_home_link": True})