from datetime import date, datetime
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.assignment.service import AssignmentService
from app.auth.dependencies import get_current_user
from app.config import settings
from app.user.models import Users

router = APIRouter(
    prefix="/pages",
    tags=["Фронт"]
)

templates = Jinja2Templates(directory="app/templates")


@router.get("/auth/register")
async def register(request: Request):
    return templates.TemplateResponse(name="register.html", context={"request": request})


@router.get("/auth/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse(name="login.html", context={"request": request})


@router.get("/tutor-home")
async def tutor_home(request: Request, current_user: Users = Depends(get_current_user)):
    assignments = await AssignmentService.find_all(user_id=current_user.id)
    return templates.TemplateResponse(
        name="tutor-home.html",
        context={"request": request, "assignments": assignments}
    )


@router.get("/assignments/{assignment_id}", response_class=HTMLResponse)
async def get_assignment_page(request: Request, assignment_id: int, current_user: Users = Depends(get_current_user)):
    """Отображение страницы задания через шаблон"""
    assignment = await AssignmentService.find_one_or_none(id=assignment_id, user_id=current_user.id)
    return templates.TemplateResponse("assignment.html", {
        "request": request,
        "assignment": assignment
    })
