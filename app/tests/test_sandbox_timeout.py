import subprocess

import nbformat
import pytest

from app.exceptions import ResourceLimitExceededException
from app.submissions.services.sandbox_runner import SandboxNotebookRunner


def _make_notebook_bytes(source: str) -> bytes:
    notebook = nbformat.v4.new_notebook(
        cells=[nbformat.v4.new_code_cell(source)]
    )
    return nbformat.writes(notebook).encode("utf-8")


def test_execute_notebook_maps_timeout_to_resource_limit(monkeypatch):
    notebook_bytes = _make_notebook_bytes("x = 1")

    def _raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["docker"], timeout=5)

    monkeypatch.setattr(
        "app.submissions.services.sandbox_runner.subprocess.run",
        _raise_timeout,
    )

    with pytest.raises(ResourceLimitExceededException):
        SandboxNotebookRunner.execute_notebook(notebook_bytes, [], 5)


def test_grade_notebook_maps_timeout_to_resource_limit(monkeypatch):
    submission_bytes = _make_notebook_bytes("x = 1")
    tutor_bytes = _make_notebook_bytes("x = 1")

    def _raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["docker"], timeout=5)

    monkeypatch.setattr(
        "app.submissions.services.sandbox_runner.subprocess.run",
        _raise_timeout,
    )

    with pytest.raises(ResourceLimitExceededException):
        SandboxNotebookRunner.grade_notebook(
            submission_bytes,
            tutor_bytes,
            [],
            5,
        )
