from sqladmin import ModelView
from app.assignment.models import Assignments 
from app.user.models import RefreshToken, Users


class UsersAdmin(ModelView, model=Users):
    column_list = [Users.id, Users.email, Users.role]
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
