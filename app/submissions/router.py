import logging
from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from app.assignment.schemas import SortEnum
from app.auth.dependencies import check_student_role, get_current_user
from app.exceptions import (
    SolutionNotFoundException,
)
from app.submissions.schemas import SubmissionQueryParams
from app.submissions.services.service import (
    SubmissionFilesService,
    SubmissionsService,
)
from app.submissions.services.notebook_service import NotebookService
from app.submissions.services.submission_manager_service import (
    SubmissionManagerService,
)
from app.user.models import Users
from app.logger import configure_logging
from app.user.router import refresh_token
from app.dropbox.service import dropbox_service

logger = logging.getLogger(__name__)
configure_logging()


router = APIRouter(prefix="/assignments", tags=["Submissions"])
sub_router = APIRouter(prefix="/submissions", tags=["Submissions"])


@router.post(
    "/{assignment_id}/submissions",
    status_code=201,
    dependencies=[Depends(refresh_token), Depends(check_student_role)],
)
async def add_submission(
    assignment_id: str,
    submission_file: UploadFile = File(...),
    current_user: Users = Depends(get_current_user),
):
    """Загрузка решения"""
    submission_id = (
        await SubmissionManagerService.process_and_upload_submission(
            assignment_id, submission_file, current_user.id, current_user.email
        )
    )

    return {
        "status": "ok",
        "submission_id": submission_id,
    }


@router.post(
    "/{assignment_id}/submissions/evaluate",
    dependencies=[Depends(refresh_token), Depends(check_student_role)],
)
async def evaluate_submission(
    assignment_id: str, current_user: Users = Depends(get_current_user)
):
    """Проверка решения"""
    submission_service = (
        await NotebookService.check_date_and_attempts_submission(
            assignment_id, current_user
        )
    )

    total_points, feedback = await SubmissionManagerService.evaluate_submission(
        assignment_id, current_user.email, submission_service
    )

    return {"message": "ok", "score": total_points, "feedback": feedback}


@sub_router.get(
    "/", dependencies=[Depends(refresh_token), Depends(check_student_role)]
)
async def get_submissions(
    current_user: Users = Depends(get_current_user),
    params: SubmissionQueryParams = Depends(),
    search: str | None = Query(None, description="Поиск по названию задания"),
):
    """Получение списка всех решений с сортировкой и поиском"""
    offset = (params.page - 1) * params.limit
    order_by = "created_at"
    desc_order = params.sort == SortEnum.newest
    total = await SubmissionsService.count(
        search=search, user_id=current_user.id
    )

    submissions = await SubmissionsService.find_all(
        user_id=current_user.id,
        skip=offset,
        limit=params.limit,
        order_by=order_by,
        desc_order=desc_order,
        search=search,
    )
    return {"submissions": submissions, "total": total}


@sub_router.get(
    "/{submission_id}",
    dependencies=[Depends(refresh_token), Depends(check_student_role)],
)
async def get_submission(
    submission_id: str, current_user: Users = Depends(get_current_user)
):
    """Получение конкретного решения"""
    submission = await SubmissionsService.find_one_or_none(
        id=submission_id, user_id=current_user.id
    )
    if not submission:
        raise SolutionNotFoundException
    return submission


@sub_router.get(
    "/{submission_id}/file",
    dependencies=[Depends(refresh_token), Depends(get_current_user)],
)
async def get_file_of_submission(submission_id: str):
    """Скачивание файла с решением"""
    submission = await SubmissionsService.find_one_or_none(id=submission_id)
    if not submission:
        raise SolutionNotFoundException

    submission = await SubmissionFilesService.find_one_or_none(
        submission_id=submission_id
    )

    content = dropbox_service.download_file(submission.file_id)
    return Response(
        content=content,
        media_type="application/x-jupyter-notebook",
        headers={
            "Content-Disposition": f"attachment; filename={submission.submission_id}_mod.ipynb"
        },
    )


@sub_router.delete(
    "/{submission_id}",
    dependencies=[Depends(refresh_token), Depends(check_student_role)],
)
async def delete_submission(
    submission_id: str, current_user: Users = Depends(get_current_user)
):
    """Удаление решения"""
    submission = await SubmissionsService.find_one_or_none(
        id=submission_id, user_id=current_user.id
    )
    if not submission:
        raise SolutionNotFoundException
    await SubmissionFilesService.delete(submission_id=submission_id)
    await SubmissionsService.delete(id=submission_id, user_id=current_user.id)
    return {"message": "Решение удалено"}
