import asyncio
import json
import logging
from sqlalchemy import insert
import pytest
from httpx import AsyncClient
from app.db import Base, async_session_maker, engine
from app.config import settings
from app.db import DATABASE_URL
from app.logger import configure_logging
from app.user.models import Users, RefreshToken
from app.assignment.models import Assignments
from app.submissions.models import Submissions


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


    async with async_session_maker() as session:
        add_users = insert(Users).values(users)
        await session.execute(add_users)
        await session.commit()

@pytest.fixture(scope="session")
def event_loop(request):
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def async_client():
    async with AsyncClient(base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="session")
async def auth_admin_ac():
    async with AsyncClient() as ac:
        await ac.post("http://127.0.0.1:8000/auth/login", json={"email": "admin@example.com", "password": "password"})
        assert ac.cookies["access_token"]
        yield ac


@pytest.fixture(scope="session")
async def auth_tutor_ac():
    async with AsyncClient() as ac:
        await ac.post("http://127.0.0.1:8000/auth/login", json={"email": "tutor@example.com", "password": "password"})
        assert ac.cookies["access_token"]
        yield ac


@pytest.fixture(scope="session")
async def auth_student_ac():
    async with AsyncClient() as ac:
        await ac.post("http://127.0.0.1:8000/auth/login", json={"email": "student@example.com", "password": "password"})
        assert ac.cookies["access_token"]
        yield ac

@pytest.fixture(scope="function")
async def session():
    async with async_session_maker() as session:
        yield session