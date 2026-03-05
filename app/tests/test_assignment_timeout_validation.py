from datetime import date, time
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.assignment.router as assignment_router_module


@pytest.fixture
def client(monkeypatch):
    app = FastAPI()
    app.include_router(assignment_router_module.router)

    async def _refresh_override():
        return {"access_token": "test"}

    async def _role_override():
        return None

    async def _current_user_override():
        return SimpleNamespace(
            id=1,
            email="tutor@example.com",
            role="TUTOR",
        )

    async def _db_override():
        yield SimpleNamespace()

    app.dependency_overrides[assignment_router_module.refresh_token] = (
        _refresh_override
    )
    app.dependency_overrides[assignment_router_module.check_tutor_role] = (
        _role_override
    )
    app.dependency_overrides[assignment_router_module.get_current_user] = (
        _current_user_override
    )
    app.dependency_overrides[assignment_router_module.get_db_session] = (
        _db_override
    )

    async def _discipline_exists(*args, **kwargs):
        return SimpleNamespace(id=1)

    async def _process_assignment(*args, **kwargs):
        return ("assignment-id", b"original", b"modified")

    async def _noop_background(*args, **kwargs):
        return None

    async def _assignment_exists(*args, **kwargs):
        return SimpleNamespace(
            start_date=date(2026, 3, 1),
            due_date=date(2026, 3, 10),
            start_time=time(10, 0),
            due_time=time(11, 0),
        )

    async def _noop_update(*args, **kwargs):
        return None

    monkeypatch.setattr(
        assignment_router_module.DisciplinesDAO,
        "find_one_or_none",
        _discipline_exists,
    )
    monkeypatch.setattr(
        assignment_router_module.AssignmentManagerService,
        "process_and_upload_assignment",
        _process_assignment,
    )
    monkeypatch.setattr(
        assignment_router_module.AssignmentManagerService,
        "upload_to_dropbox_and_finalize",
        _noop_background,
    )
    monkeypatch.setattr(
        assignment_router_module.AssignmentManagerService,
        "upload_resource_files",
        _noop_background,
    )
    monkeypatch.setattr(
        assignment_router_module.AssignmentDAO,
        "find_one_or_none",
        _assignment_exists,
    )
    monkeypatch.setattr(
        assignment_router_module.AssignmentDAO,
        "update",
        _noop_update,
    )

    with TestClient(app) as test_client:
        yield test_client


def _post_assignment(client: TestClient, timeout_seconds: int):
    data = {
        "name": "Timeout test",
        "number_of_attempts": "1",
        "execution_timeout_seconds": str(timeout_seconds),
        "discipline_id": "1",
        "start_date": "2026-03-01",
        "start_time": "10:00",
        "due_date": "2026-03-02",
        "due_time": "10:00",
    }
    files = {
        "assignment_file": (
            "task.ipynb",
            b"{}",
            "application/x-jupyter-notebook",
        )
    }
    return client.post("/assignments/", data=data, files=files)


@pytest.mark.parametrize("timeout_seconds", [0, 1001])
def test_post_assignment_rejects_out_of_range_timeout(client, timeout_seconds):
    response = _post_assignment(client, timeout_seconds)
    assert response.status_code == 422


@pytest.mark.parametrize("timeout_seconds", [1, 1000])
def test_post_assignment_accepts_boundary_timeout(client, timeout_seconds):
    response = _post_assignment(client, timeout_seconds)
    assert response.status_code == 201


@pytest.mark.parametrize("timeout_seconds", [0, 1001])
def test_patch_assignment_rejects_out_of_range_timeout(client, timeout_seconds):
    response = client.patch(
        "/assignments/assignment-id",
        json={"execution_timeout_seconds": timeout_seconds},
    )
    assert response.status_code == 422


@pytest.mark.parametrize("timeout_seconds", [1, 1000])
def test_patch_assignment_accepts_boundary_timeout(client, timeout_seconds):
    response = client.patch(
        "/assignments/assignment-id",
        json={"execution_timeout_seconds": timeout_seconds},
    )
    assert response.status_code == 200
