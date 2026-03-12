import pytest

from app.submissions.services.submission_manager_service import SubmissionManagerService


class _FakeUploadFile:
    def __init__(self, filename: str, payload: bytes):
        self.filename = filename
        self._payload = payload

    async def read(self):
        return self._payload


@pytest.mark.asyncio
async def test_upload_path_uses_bytes_pipeline(monkeypatch):
    expected_id = "sub-id"

    async def _fake_bytes_pipeline(*args, **kwargs):
        return expected_id

    monkeypatch.setattr(
        SubmissionManagerService,
        "process_and_upload_submission_bytes",
        _fake_bytes_pipeline,
    )

    upload = _FakeUploadFile("solution.ipynb", b"{}")
    result = await SubmissionManagerService.process_and_upload_submission(
        session=None,
        assignment_id="assignment-id",
        submission_file=upload,
        user_id=1,
        user_email="student@example.com",
    )

    assert result == expected_id
