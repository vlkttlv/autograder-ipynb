from app.assignment.models import AssignmentFile, Assignments
from app.service.base import BaseService


class AssignmentService(BaseService):
    
    model = Assignments


    @classmethod
    async def update_assignment(cls, model_id, updated_data):
        """
        Обновляет запись в БД"
        """
        if updated_data.name is not None:
            await cls.update(model_id, name=updated_data.name)
        if updated_data.start_date is not None:
            await cls.update(model_id, start_date=updated_data.start_date)
        if updated_data.start_time is not None:
            await cls.update(model_id, start_time=updated_data.start_time)
        if updated_data.due_date is not None:
            await cls.update(model_id, due_date=updated_data.due_date)
        if updated_data.due_time is not None:
            await cls.update(model_id, due_time=updated_data.due_time)
        if updated_data.number_of_attempts is not None:
            await cls.update(model_id, number_of_attempts=updated_data.number_of_attempts)


class AssignmentFileService(BaseService):
    
    model = AssignmentFile