import json
from numpy import insert
import pytest
from httpx import AsyncClient
from app.db import Base, async_session_maker, engine
from app.config import settings
from app.user.models import Users, RefreshToken
from app.assignment.models import Assignments
from app.submissions.models import Submissions
from app.main import app as fastapi_app


@pytest.fixture(autouse=True, scope="session")
async def prepare_database():
    assert settings.MODE == "TEST"
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    def open_test_json(model: str):
        with open(f"tests/mock_data/{model}.json", "r", encoding='utf-8 ') as file:
            return json.load(file)

    users = open_test_json("users")


    async with async_session_maker() as session:
        add_users = insert(Users).values(users)
        await session.execute(add_users)

        await session.commit()


@pytest.fixture(scope="session")
async def ac():
    async with AsyncClient(base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="session")
async def auth_admin_ac():
    async with AsyncClient(base_url="http://test") as ac:
        await ac.post("auth/login", json={"email": "admin@example.com", "password": "password"})
        assert ac.cookies["access_token"]
        yield ac


@pytest.fixture(scope="session")
async def auth_tutor_ac():
    async with AsyncClient(base_url="http://test") as ac:
        await ac.post("auth/login", json={"email": "tutor@example.com", "password": "password"})
        assert ac.cookies["access_token"]
        yield ac


@pytest.fixture(scope="session")
async def auth_student_ac():
    async with AsyncClient(app=fastapi_app, base_url="http://test") as ac:
        await ac.post("auth/login", json={"email": "student@example.com", "password": "password"})
        assert ac.cookies["access_token"]
        yield ac

@pytest.fixture(scope="function")
async def session():
    async with async_session_maker() as session:
        yield session