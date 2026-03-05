import nbformat
import pytest

from app.exceptions import UnsafeNotebookCodeException
from app.submissions.services.sandbox_runner import _scan_notebook_for_malicious_code


def _make_notebook_bytes(cells: list[nbformat.NotebookNode]) -> bytes:
    notebook = nbformat.v4.new_notebook(cells=cells)
    return nbformat.writes(notebook).encode("utf-8")


def test_scan_allows_safe_notebook():
    notebook_bytes = _make_notebook_bytes(
        [
            nbformat.v4.new_markdown_cell("`rm -rf` in markdown should not block"),
            nbformat.v4.new_code_cell("x = 1\nprint(x + 1)"),
        ]
    )

    _scan_notebook_for_malicious_code(notebook_bytes)


@pytest.mark.parametrize(
    "source",
    [
        "!rm -rf /tmp/test",
        "import os\nos.remove('data.csv')",
        "query = 'DROP TABLE students;'",
        "query = 'DELETE FROM submissions;'",
    ],
)
def test_scan_blocks_malicious_patterns(source: str):
    notebook_bytes = _make_notebook_bytes([nbformat.v4.new_code_cell(source)])

    with pytest.raises(UnsafeNotebookCodeException):
        _scan_notebook_for_malicious_code(notebook_bytes)
