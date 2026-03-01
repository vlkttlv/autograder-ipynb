import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable

from app.exceptions import (
    ResourceLimitExceededException,
    SandboxExecutionException,
    SyntaxException,
)

logger = logging.getLogger(__name__)

SANDBOX_DOCKER_IMAGE = "autograder-ipynb:latest"
SANDBOX_CPU_LIMIT = "1"
SANDBOX_MEMORY_LIMIT = "1g"
SANDBOX_PIDS_LIMIT = "256"


def _docker_mount_source(workspace: Path) -> str:
    """Преобразование пути хоста для привязки Docker, включая хосты Windows"""
    resolved = str(workspace.resolve())
    if re.match(r"^[A-Za-z]:\\", resolved):
        drive = resolved[0].lower()
        tail = resolved[2:].replace("\\", "/")
        return f"/host_mnt/{drive}{tail}"
    return resolved


def _write_resources(workspace: Path, resources: Iterable[tuple[str, bytes]]):
    """Создает файлы задания, сохраняя относительные подкаталоги"""
    for filename, content in resources:
        resource_path = Path(filename)
        if resource_path.is_absolute() or ".." in resource_path.parts:
            logger.warning("Skipping unsafe resource path: %s", filename)
            continue
        safe_parts = [part for part in resource_path.parts if part not in ("", ".")]
        if not safe_parts:
            continue
        target = workspace.joinpath(*safe_parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)


def _run_in_container(command: list[str], workspace: Path, timeout_seconds: int):
    docker_command = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--cpus",
        SANDBOX_CPU_LIMIT,
        "--memory",
        SANDBOX_MEMORY_LIMIT,
        "--pids-limit",
        str(SANDBOX_PIDS_LIMIT),
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--mount",
        f"type=bind,source={_docker_mount_source(workspace)},target=/workspace",
        "-w",
        "/workspace",
        SANDBOX_DOCKER_IMAGE,
        *command,
    ]

    try:
        return subprocess.run(
            docker_command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error("Заупск Sandbox docker завершился ошибкой с кодом %s. stderr: %s", e.returncode, e.stderr)
        raise SandboxExecutionException from e
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.error("Ошибка выполнения в песочнице: %s", e)
        raise SandboxExecutionException from e


class SandboxNotebookRunner:
    @staticmethod
    def execute_notebook(
        notebook_content: bytes,
        resources: list[tuple[str, bytes]],
        timeout_seconds: int,
    ) -> bytes:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            (workspace / "submission.ipynb").write_bytes(notebook_content)
            _write_resources(workspace, resources)

            script = (
                "import nbformat\n"
                "from nbclient import NotebookClient\n"
                "from nbclient.exceptions import CellExecutionError\n"
                "nb = nbformat.read('/workspace/submission.ipynb', as_version=4)\n"
                "client = NotebookClient(nb, kernel_name='python3')\n"
                "try:\n"
                "    client.execute()\n"
                "except CellExecutionError as e:\n"
                "    if 'AssertionError' not in str(e):\n"
                "        raise\n"
                "nbformat.write(nb, '/workspace/submission.ipynb')\n"
            )
            try:
                logger.info("Началась проверка блокнота")
                _run_in_container(["python", "-c", script], workspace, timeout_seconds)
            except SandboxExecutionException as e:
                cause = e.__cause__
                if isinstance(cause, subprocess.CalledProcessError):
                    stderr = (cause.stderr or "").lower()
                    if "deadkernelerror" in stderr or "kernel died" in stderr or "killed" in stderr:
                        raise ResourceLimitExceededException from e
                    if cause.returncode == 1:
                        raise SyntaxException from e
                raise
            except Exception as e:
                raise SyntaxException from e

            return (workspace / "submission.ipynb").read_bytes()

    @staticmethod
    def grade_notebook(
        submission_content: bytes,
        tutor_content: bytes,
        resources: list[tuple[str, bytes]],
        timeout_seconds: int,
    ) -> tuple[int, list[int]]:
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace = Path(tmp_dir)
            (workspace / "submission.ipynb").write_bytes(submission_content)
            (workspace / "tutor.ipynb").write_bytes(tutor_content)
            _write_resources(workspace, resources)

            script = (
                "import json\n"
                "import re\n"
                "import nbformat\n"
                "from nbclient import NotebookClient\n"
                "from nbclient.exceptions import CellExecutionError\n"
                "submission = nbformat.read('/workspace/submission.ipynb', as_version=4)\n"
                "tutor = nbformat.read('/workspace/tutor.ipynb', as_version=4)\n"
                "client = NotebookClient(submission, kernel_name='python3')\n"
                "total_points = 0\n"
                "feedback = []\n"
                "with client.setup_kernel():\n"
                "    for index, cell in enumerate(submission.cells):\n"
                "        if cell.cell_type != 'code':\n"
                "            continue\n"
                "        try:\n"
                "            client.execute_cell(cell, cell_index=index, store_history=True)\n"
                "        except CellExecutionError:\n"
                "            pass\n"
                "        if '# Tests ' in cell.source and ' points.' in cell.source:\n"
                "            points = 0\n"
                "            match = re.search(r'# Tests (\\d+) points', cell.source)\n"
                "            if match:\n"
                "                points = int(match.group(1))\n"
                "            cell.source = tutor.cells[index].source\n"
                "            try:\n"
                "                client.execute_cell(cell, index)\n"
                "                total_points += points\n"
                "            except CellExecutionError:\n"
                "                feedback.append(index)\n"
                "print(json.dumps({'total_points': total_points, 'feedback': feedback}))\n"
            )
            try:
                logger.info("Началась оценка блокнота")
                result = _run_in_container(["python", "-c", script], workspace, timeout_seconds)
            except SandboxExecutionException as e:
                cause = e.__cause__
                if isinstance(cause, subprocess.CalledProcessError):
                    stderr = (cause.stderr or "").lower()
                    if "deadkernelerror" in stderr or "kernel died" in stderr or "killed" in stderr:
                        raise ResourceLimitExceededException from e
                raise
            try:
                payload = json.loads(result.stdout.strip().splitlines()[-1])
            except (json.JSONDecodeError, IndexError) as e:
                raise SandboxExecutionException from e

            return payload["total_points"], payload["feedback"]
