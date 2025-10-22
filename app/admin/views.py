from sqladmin import ModelView
from app.assignment.models import AssignmentFile, Assignments 
from app.user.models import Disciplines, Groups, RefreshToken, Users
from app.submissions.models import SubmissionFiles, Submissions


class UsersAdmin(ModelView, model=Users):
    column_list = [Users.id, Users.first_name, Users.last_name, Users.email, Users.role, Users.group_id, Users.group]
    column_details_exclude_list = [Users.hashed_password]
    name = "Пользователь"
    name_plural = "Пользователи"


class RefreshTokensAdmin(ModelView, model=RefreshToken):
    column_list = [c.name for c in RefreshToken.__table__.c] + [RefreshToken.user]
    name = "Токен"
    name_plural = "Токены"

class GroupsAdmin(ModelView, model=Groups):
    column_list = [c.name for c in Groups.__table__.c] + [Groups.students]
    name = "Группа"
    name_plural = "Группы"

class DisciplinesAdmin(ModelView, model=Disciplines):
    column_list = [c.name for c in Disciplines.__table__.c] + [Disciplines.teacher]
    name = "Дисциплина"
    name_plural = "Дисциплины"

class AssignmentsAdmin(ModelView, model=Assignments):
    column_list = [c.name for c in Assignments.__table__.c] + [Assignments.user]
    name = "Задание"
    name_plural = "Задания"

class AssignmentFilesAdmin(ModelView, model=AssignmentFile):
    column_list = [c.name for c in AssignmentFile.__table__.c] + [AssignmentFile.assignment]
    name = "Файл задания"
    name_plural = "Файлы заданий"


class SubmissionsAdmin(ModelView, model=Submissions):
    column_list = [c.name for c in Submissions.__table__.c] + [Submissions.user]
    name = "Решение"
    name_plural = "Решения"


class SubmissionFilesAdmin(ModelView, model=SubmissionFiles):
    column_list = [c.name for c in SubmissionFiles.__table__.c] + [SubmissionFiles.submission]
    name = "Файл решения"
    name_plural = "Файлы решений"