import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqladmin import Admin

from app.admin.views import (
    AssignmentsAdmin,
    SubmissionsAdmin,
    UsersAdmin,
    RefreshTokensAdmin,
    AssignmentFilesAdmin,
    GroupsAdmin,
    DisciplinesAdmin,
    SubmissionFilesAdmin,
)
from app.user.router import router as user_router
from app.user.google_router import router as google_router
from app.assignment.router import router as assignment_router
from app.submissions.router import router as submission_router
from app.submissions.router import sub_router as two_submission_router
from app.logger import configure_logging, setup_fastapi_exception_logging
from app.pages.router import router as frontend
from app.admin.auth import authentication_backend
from app.db import engine


app = FastAPI()

configure_logging()
setup_fastapi_exception_logging(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(user_router)
app.include_router(google_router)
app.include_router(assignment_router)
app.include_router(submission_router)
app.include_router(two_submission_router)
app.include_router(frontend)

admin = Admin(app, engine, authentication_backend=authentication_backend)
admin.add_view(UsersAdmin)
admin.add_view(AssignmentsAdmin)
admin.add_view(RefreshTokensAdmin)
admin.add_view(SubmissionsAdmin)
admin.add_view(AssignmentFilesAdmin)
admin.add_view(GroupsAdmin)
admin.add_view(DisciplinesAdmin)
admin.add_view(SubmissionFilesAdmin)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app.mount(
    "/static",
    StaticFiles(directory=os.path.join(BASE_DIR, "static")),
    name="static",
)
app.mount(
    "/assignment", StaticFiles(directory="app/assignment"), name="assignment"
)
