import logging
import nbformat
from fastapi import APIRouter, Depends, File, Response, UploadFile
from nbclient import NotebookClient
from nbformat import read, NO_CONVERT
from app.assignment.schemas import TypeOfAssignmentFile
from app.assignment.service import AssignmentFileService
from app.auth.dependencies import check_student_role, get_current_user
from app.exceptions import (DecodingIPYNBException,
                            IncorrectFormatAssignmentException,
                            SolutionNotFoundException,
                            SyntaxException)
from app.submissions.service import SubmissionFilesService, SubmissionsService
from app.submissions.utils import (check_date_and_attempts_submission,
                                   check_date_submission,
                                   grade_notebook)
from app.user.models import Users
from app.logger import configure_logging

logger = logging.getLogger(__name__)
configure_logging()


router = APIRouter(prefix="/assignments", tags=['Submissions'])
sub_router = APIRouter(prefix="/submissions", tags=["Submissions"])

@router.post("/{assignment_id}/submissions", status_code=201, dependencies=[Depends(check_student_role)])
async def add_submission(
    assignment_id: str,
    submission_file: UploadFile = File(...),
    current_user: Users = Depends(get_current_user)
):
    """Загрузка решения"""
    await check_date_submission(assignment_id)

    filename = submission_file.filename
    if not filename.endswith(".ipynb"):
        raise IncorrectFormatAssignmentException

    notebook = read(submission_file.file, as_version=NO_CONVERT)
    client = NotebookClient(notebook)

    try:
        client.execute()
    except Exception as e:
        raise SyntaxException from e

    submission = await SubmissionsService.find_one_or_none(user_id=current_user.id, assignment_id=assignment_id)
    if submission is None:
        submission = await SubmissionsService.add(user_id=current_user.id,
                                    assignment_id=assignment_id,
                                    score=0,
                                    number_of_attempts=0)
        sub_file = await SubmissionFilesService.find_one_or_none(submission_id=submission)
    else:
        sub_file = await SubmissionFilesService.find_one_or_none(submission_id=submission.id)
    submission_notebook = nbformat.writes(notebook).encode("utf-8")

    if sub_file is None:
        await SubmissionFilesService.add(submission_id=submission.id,
                                         assignment_id=assignment_id,
                                        content=submission_notebook)
    else:
        await SubmissionFilesService.update(model_id=sub_file.id,
                                            content=submission_notebook)
    logger.info("Пользователь %s загрузил решение для задания %s", current_user.email, assignment_id)
    return {"message": "ok",
            "submission": submission}

                
@router.post("/{assignment_id}/submissions/evaluate", dependencies=[Depends(check_student_role)])
async def evaluate_submission(
    assignment_id: str,
    current_user: Users = Depends(get_current_user)
):
    """Проверка решения"""
    submission_service = await check_date_and_attempts_submission(assignment_id, current_user)
    submission = await SubmissionFilesService.find_one_or_none(submission_id=submission_service.id)
    if not submission or not submission_service:
        raise SolutionNotFoundException
    try:
        notebook = nbformat.reads(submission.content.decode("utf-8"), as_version=4)
    except Exception as e:
        raise DecodingIPYNBException from e
    assignment = await AssignmentFileService.find_one_or_none(assignment_id=assignment_id,
                                                              file_type=TypeOfAssignmentFile.ORIGINAL)
    try:
        tutor_notebook = nbformat.reads(assignment.content.decode("utf-8"), as_version=4)
    except Exception as e:
        raise DecodingIPYNBException from e

    client = NotebookClient(notebook)
    # Выполняем каждую ячейку отдельно
    total_points = grade_notebook(client, notebook, tutor_notebook)
    await SubmissionsService.update(model_id=submission_service.id,
                                    score=total_points,
                                    number_of_attempts=submission_service.number_of_attempts + 1)

    logger.info("Пользователь %s проверил решение задания %s", current_user.email, assignment_id)

    return {"message": "ok",
            "score": total_points}

@sub_router.get("/", dependencies=[Depends(check_student_role)])
async def get_submissions(current_user: Users = Depends(get_current_user)):
    """Получение списка всех решений"""
    return await SubmissionsService.find_all(user_id=current_user.id)


@sub_router.get("/{submission_id}", dependencies=[Depends(check_student_role)])
async def get_submission(submission_id: str, current_user: Users = Depends(get_current_user)):
    """Получение конкретного решения"""
    submission = await SubmissionsService.find_one_or_none(id=submission_id, user_id=current_user.id)
    if not submission:
        raise SolutionNotFoundException
    return submission

@sub_router.get("/{submission_id}/file", dependencies=[Depends(get_current_user)])
async def get_file_of_submission(submission_id: str, user_id: int):
    """Скачивание файла с решением"""
    submission = await SubmissionsService.find_one_or_none(id=submission_id, user_id=user_id)
    if not submission:
        raise SolutionNotFoundException
    submission = await SubmissionFilesService.find_one_or_none(submission_id=submission_id)
    return Response(content=submission.content,
                    media_type='application/x-jupyter-notebook',
                    headers={"Content-Disposition": f"attachment; filename={submission.submission_id}.ipynb"})

@sub_router.delete("/{submission_id}", dependencies=[Depends(check_student_role)])
async def delete_submission(submission_id: str, current_user: Users = Depends(get_current_user)):
    """Удаление решения"""
    submission = await SubmissionsService.find_one_or_none(id=submission_id,
                                                           user_id=current_user.id)
    if not submission:
        raise SolutionNotFoundException
    await SubmissionFilesService.delete(submission_id=submission_id)
    await SubmissionsService.delete(id=submission_id, user_id=current_user.id)
    return {"message": "Решение удалено"}
