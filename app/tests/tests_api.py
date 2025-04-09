import pytest
from httpx import AsyncClient
import os

@pytest.mark.asyncio(scope="session")
async def test_add_assignment(auth_admin_ac: AsyncClient):

    filename = "app/tests/mock_data/mock_assignments/assig2.ipynb"

    with open(filename, "rb") as f:
        response = await auth_admin_ac.post(
            "http://127.0.0.1:8000/assignments/test",
            files={"assignment_file": (filename, f, "application/x-ipynb+json")}
        )

    assert response.status_code == 200
