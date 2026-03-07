import pytest

from app.exceptions import EmbeddedEditorDisabledException
from app.submissions.services.embedded_notebook_service import EmbeddedNotebookService


def test_embedded_notebook_service_paths():
    assignment_id = "123e4567-e89b-12d3-a456-426614174000"
    user_id = 42

    assert EmbeddedNotebookService.notebook_path(assignment_id).startswith(
        f"assignments/{assignment_id}/"
    )
    assert EmbeddedNotebookService.draft_dropbox_path(assignment_id, user_id).startswith(
        f"/drafts/{assignment_id}/{user_id}/"
    )


def test_embedded_notebook_service_disabled_flag(monkeypatch):
    monkeypatch.setattr(
        "app.submissions.services.embedded_notebook_service.settings.ENABLE_EMBEDDED_NOTEBOOK_EDITOR",
        False,
    )
    with pytest.raises(EmbeddedEditorDisabledException):
        EmbeddedNotebookService.ensure_enabled()
