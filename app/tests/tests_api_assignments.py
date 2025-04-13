import pytest
from httpx import AsyncClient

@pytest.mark.asyncio(scope="session")
async def test_add_assignment(auth_tutor_ac: AsyncClient):
    wrong_assignment_1 = "app/tests/mock_data/mock_assignments/assig_wrong_1.ipynb"
    wrong_assignment_2 = "app/tests/mock_data/mock_assignments/assig_wrong_2.ipynb"
    assignment = "app/tests/mock_data/mock_assignments/assig2.ipynb"

    with open(wrong_assignment_1, "rb") as f:
        response = await auth_tutor_ac.post(
            "http://127.0.0.1:8000/assignments/test",
            files={"assignment_file": (wrong_assignment_1, f, "application/x-ipynb+json")},
            timeout=30.0
        )

    assert response.status_code == 400
    assert response.json()['detail'] == "Не найдены решения"

    with open(wrong_assignment_2, "rb") as f:
        response = await auth_tutor_ac.post(
            "http://127.0.0.1:8000/assignments/test",
            files={"assignment_file": (wrong_assignment_2, f, "application/x-ipynb+json")},
            timeout=30.0
        )

    assert response.status_code == 400
    assert response.json()['detail'] == "Не найдены скрытые тесты"


    with open(assignment, "rb") as f:
        response = await auth_tutor_ac.post(
            "http://127.0.0.1:8000/assignments/",
            params={
                "name": "Test Assignment",
                "number_of_attempts": 3,
                "start_date": "2025-10-01",
                "due_date": "2025-10-31",
                "start_time": "10:00",
                "due_time": "20:00",
            },
            files={"assignment_file": (assignment, f, "application/x-ipynb+json")},
            timeout=30.0
        )

    assert response.status_code == 201

    with open(assignment, "rb") as f:
        response = await auth_tutor_ac.post(
            "http://127.0.0.1:8000/assignments/",
            params={
                "name": "Test Assignment",
                "number_of_attempts": 3,
                "start_date": "2025-10-01",
                "due_date": "2025-10-31",
                "start_time": "10:00",
                "due_time": "20:00",
            },
            files={"assignment_file": (assignment, f, "application/x-ipynb+json")},
            timeout=30.0
        )



@pytest.mark.asyncio(scope="session")
async def test_get_assighment(auth_tutor_ac: AsyncClient):
    response = await auth_tutor_ac.get("http://127.0.0.1:8000/assignments/1")
    assert response.status_code == 200
    assert response.json() == {
                                "name": "Test Assignment",
                                "start_date": "2025-10-01",
                                "due_date": "2025-10-31",
                                "start_time": "10:00:00",
                                "due_time": "20:00:00",
                                "number_of_attempts": 3,
                                "user_id": 2,
                                "grade": 15
                                }

    response = await auth_tutor_ac.get("http://127.0.0.1:8000/assignments/2")
    assert response.json() == None

@pytest.mark.asyncio(scope="session")
async def test_get_assighments(auth_tutor_ac: AsyncClient):
    response = await auth_tutor_ac.get("http://127.0.0.1:8000/assignments/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio(scope="session")
async def test_update_assighment(auth_tutor_ac: AsyncClient):
    response = await auth_tutor_ac.patch("http://127.0.0.1:8000/assignments/5",
                                   json={"name": "New Name"})
    assert response.status_code == 404
    response = await auth_tutor_ac.patch("http://127.0.0.1:8000/assignments/1",
                                json={"name": "New Name"})
    assert response.status_code == 200


@pytest.mark.asyncio(scope="session")
async def test_delete_assighment(auth_tutor_ac: AsyncClient):
    response = await auth_tutor_ac.delete("http://127.0.0.1:8000/assignments/1")
    assert response.status_code == 204
    response = await auth_tutor_ac.delete("http://127.0.0.1:8000/assignments/10")
    assert response.status_code == 404



@pytest.mark.asyncio(scope="session")
async def test_get_stats(auth_tutor_ac: AsyncClient):
    pass