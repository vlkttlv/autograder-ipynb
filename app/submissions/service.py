from app.service.base import BaseService
from app.submissions.models import Submissions


class SubmissionsService(BaseService):

    model = Submissions