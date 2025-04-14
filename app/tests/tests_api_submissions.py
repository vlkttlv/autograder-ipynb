import pytest
from httpx import AsyncClient

@pytest.mark.asyncio(scope="session")
async def test_download_assignment(auth_student_ac: AsyncClient):
    response = await auth_student_ac.get("http://127.0.0.1:8000/submissions/2/download")
    assert response.status_code == 200
    assert response.headers['content-type'] == 'application/x-jupyter-notebook'

