import asyncio
import json
import logging
from sqlalchemy import insert
import pytest
import os
from httpx import AsyncClient, ASGITransport
from app.db import Base, async_session_maker, engine
from app.config import settings
from app.db import DATABASE_URL
from app.logger import configure_logging
from app.user.models import Users
from app.assignment.models import Assignments
from app.submissions.models import Submissions

from app.main import app as fastapi_app
logger = logging.getLogger(__name__)
configure_logging()


@pytest.fixture(autouse=True, scope="session")
async def prepare_database():
    assert settings.MODE == "TEST"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

        def open_test_json(model: str):
            with open(f"app/tests/mock_data/{model}.json", "r", encoding='utf-8') as file:
                return json.load(file)

        users = open_test_json("users")
        await conn.execute(insert(Users).values(users))


@pytest.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="session")
async def auth_admin_ac():
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as ac:
        await ac.post("/auth/login", json={"email": "admin@example.com", "password": "password"})
        assert ac.cookies["access_token"]
        yield ac


@pytest.fixture(scope="session")
async def auth_tutor_ac():
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as ac:
        await ac.post("/auth/login", json={"email": "tutor@example.com", "password": "password"})
        assert ac.cookies["access_token"]
        yield ac


@pytest.fixture(scope="session")
async def auth_student_ac():
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as ac:
        await ac.post("/auth/login", json={"email": "student@example.com", "password": "password"})
        assert ac.cookies["access_token"]
        yield ac

@pytest.fixture(scope="function")
async def session():
    async with async_session_maker() as session:
        yield session


@pytest.fixture(scope="function")
def set_temporary_dirs():
    old_original_env = os.getenv("ASSIGNMENT_ORIGINAL_DIR")
    old_modified_env = os.getenv("ASSIGNMENT_MODIFIED_DIR")

    os.environ["ASSIGNMENT_ORIGINAL_DIR"] = "app\\tests\\mock_data\\mock_assignments\\original_assignments"
    os.environ["ASSIGNMENT_MODIFIED_DIR"] = "app\\tests\\mock_data\\mock_assignments\\modified_assignments"

    yield

    # # Восстанавливаем первоначальные значения
    # if old_original_env is not None:
    #     os.environ["ASSIGNMENT_ORIGINAL_DIR"] = old_original_env
    # else:
    #     del os.environ["ASSIGNMENT_ORIGINAL_DIR"]

    # if old_modified_env is not None:
    #     os.environ["ASSIGNMENT_MODIFIED_DIR"] = old_modified_env
    # else:
    #     del os.environ["ASSIGNMENT_MODIFIED_DIR"]