from fastapi import FastAPI
from sqladmin import Admin
from app.admin.views import AssignmentsAdmin, UsersAdmin, RefreshTokensAdmin
from app.user.router import router as user_router
from app.assignment.router import router as assignment_router
from app.admin.auth import authentication_backend

from app.db import engine


app = FastAPI()
app.include_router(user_router)
app.include_router(assignment_router)

admin = Admin(app, engine, authentication_backend=authentication_backend)
admin.add_view(UsersAdmin)
admin.add_view(AssignmentsAdmin)
admin.add_view(RefreshTokensAdmin)
