from sqladmin import ModelView
from app.assignment.models import Assignments 
from app.user.models import RefreshToken, Users
from app.submissions.models import Submissions


class UsersAdmin(ModelView, model=Users):
    column_list = [Users.id, Users.first_name, Users.last_name, Users.email, Users.role]
    column_details_exclude_list = [Users.hashed_password]
    name = "Пользователь"
    name_plural = "Пользователи"


class RefreshTokensAdmin(ModelView, model=RefreshToken):
    column_list = [c.name for c in RefreshToken.__table__.c]
    name = "Токен"
    name_plural = "Токены"

class AssignmentsAdmin(ModelView, model=Assignments):
    column_list = [c.name for c in Assignments.__table__.c] + [Assignments.user]
    name = "Задание"
    name_plural = "Задания"


class SubmissionsAdmin(ModelView, model=Submissions):
    column_list = [c.name for c in Submissions.__table__.c] + [Submissions.user]
    name = "Решение"
    name_plural = "Решения"