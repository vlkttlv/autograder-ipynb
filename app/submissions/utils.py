from datetime import datetime, timedelta

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db import get_db_session
from app.exceptions import RateLimitExceededException
from app.submissions.services.service import SubmissionAttemptsDAO
from app.user.models import Users


EVALUATE_COOLDOWN_SECONDS = 10


async def enforce_submission_evaluate_rate_limit(
    assignment_id: str,
    current_user: Users = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
):
    last_attempt_at = await SubmissionAttemptsDAO.find_latest_created_at(
        session=session,
        assignment_id=assignment_id,
        user_id=current_user.id,
    )
    if last_attempt_at is None:
        return

    if datetime.utcnow() < last_attempt_at + timedelta(seconds=EVALUATE_COOLDOWN_SECONDS):
        raise RateLimitExceededException
