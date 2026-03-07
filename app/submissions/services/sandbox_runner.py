import json
import logging
import os
from contextlib import contextmanager
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable

from app.exceptions import (
    ResourceLimitExceededException,
    SandboxExecutionException,
    SyntaxException,
    UnsafeNotebookCodeException,
)

logger = logging.getLogger(__name__)

SANDBOX_DOCKER_IMAGE = "autograder-ipynb:latest"
SANDBOX_CPU_LIMIT = "1"
SANDBOX_MEMORY_LIMIT = "1g"
SANDBOX_PIDS_LIMIT = "256"
SANDBOX_VOLUMES_FROM = os.getenv("SANDBOX_VOLUMES_FROM", "autograder_app")
SANDBOX_CONTAINER_USER = os.getenv("SANDBOX_CONTAINER_USER", "0:0")
MALICIOUS_CELL_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\brm\s+-rf\b", "rm_rf"),
    (r"\bos\.remove\s*\(", "os_remove"),
    (r"\bos\.rmdir\s*\(", "os_rmdir"),
    (r"\bshutil\.rmtree\s*\(", "shutil_rmtree"),
    (r"\bos\.system\s*\([^)]*\brm\s+-rf\b", "os_system_rm_rf"),
    (r"\bsubprocess\.(?:run|call|Popen|check_call|check_output)\s*\([^)]*\brm\s+-rf\b", "subprocess_rm_rf"),
    (r"\bDROP\s+TABLE\b", "sql_drop_table"),
    (r"\bTRUNCATE\s+TABLE\b", "sql_truncate_table"),
    (r"\bDELETE\s+FROM\b", "sql_delete_from"),
    (r"\bALTER\s+TABLE\b", "sql_alter_table"),
)


def _is_running_in_docker() -> bool:
    return Path("/.dockerenv").exists()

def _docker_mount_source(workspace: Path) -> str:
    """Преобразование пути хоста для привязки Docker, включая хосты Windows"""
    resolved = str(workspace.resolve())
    if re.match(r"^[A-Za-z]:\\", resolved):
        drive = resolved[0].lower()
        tail = resolved[2:].replace("\\", "/")
        return f"/host_mnt/{drive}{tail}"
    return resolved



def _workspace_root() -> Path | None:
    if _is_running_in_docker():
        root = Path('/app/.sandbox')
        root.mkdir(parents=True, exist_ok=True)
        return root
    return None


@contextmanager
def _workspace_context():
    # Каждый запуск получает отдельный временный workspace и не делит файлы
    # с соседними проверками. После выхода директория удаляется.
    root = _workspace_root()
    with tempfile.TemporaryDirectory(dir=root) as tmp_dir:
        yield Path(tmp_dir)


def _scan_notebook_for_malicious_code(notebook_content: bytes):
    # Дополнительный pre-check до старта контейнера:
    # блокируем очевидно опасные команды на уровне исходного кода ячеек.
    try:
        import nbformat
    except Exception:
        return

    try:
        notebook = nbformat.reads(notebook_content.decode("utf-8"), as_version=4)
    except Exception:
        return

    findings: list[tuple[int, str]] = []
    for index, cell in enumerate(notebook.cells):
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", "")
        for pattern, kind in MALICIOUS_CELL_PATTERNS:
            if re.search(pattern, source, re.IGNORECASE | re.MULTILINE):
                findings.append((index, kind))
                break

    if findings:
        logger.warning(
            "Rejected notebook due to potentially malicious code. Findings: %s",
            findings,
        )
        raise UnsafeNotebookCodeException


def _build_docker_run_command(command: list[str], workspace: Path) -> list[str]:
    # Базовые ограничения sandbox-контейнера:
    # - без сетевого доступа;
    # - c лимитами CPU/RAM/PIDs;
    # - без Linux capabilities и эскалации привилегий.
    docker_command = [
        'docker',
        'run',
        '--rm',
        '--user',
        SANDBOX_CONTAINER_USER,
        '--network',
        'none',
        '--cpus',
        SANDBOX_CPU_LIMIT,
        '--memory',
        SANDBOX_MEMORY_LIMIT,
        '--pids-limit',
        str(SANDBOX_PIDS_LIMIT),
        '--cap-drop',
        'ALL',
        '--security-opt',
        'no-new-privileges',
    ]

    if _is_running_in_docker():
        docker_command.extend(['--volumes-from', SANDBOX_VOLUMES_FROM, '-w', str(workspace)])
    else:
        docker_command.extend([
            '--mount',
            f'type=bind,source={_docker_mount_source(workspace)},target=/workspace',
            '-w',
            '/workspace',
        ])

    docker_command.extend([SANDBOX_DOCKER_IMAGE, *command])
    return docker_command

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
    # Централизованный запуск и маппинг ошибок subprocess
    # в доменные исключения приложения.
    docker_command = _build_docker_run_command(command, workspace)

    try:
        return subprocess.run(
            docker_command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=True,
        )
    except subprocess.TimeoutExpired as e:
        logger.error(
            "Sandbox execution timed out after %s seconds. cmd=%s",
            timeout_seconds,
            docker_command,
        )
        raise ResourceLimitExceededException from e
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
        # Выполняем все ячейки notebook в изоляции и возвращаем уже исполненный
        # ipynb (с output'ами), который затем сохраняется как submission.
        _scan_notebook_for_malicious_code(notebook_content)
        with _workspace_context() as workspace:
            (workspace / "submission.ipynb").write_bytes(notebook_content)
            _write_resources(workspace, resources)

            script = (
                "import nbformat\n"
                "from nbclient import NotebookClient\n"
                "from nbclient.exceptions import CellExecutionError\n"
                "nb = nbformat.read('submission.ipynb', as_version=4)\n"
                "client = NotebookClient(nb, kernel_name='python3')\n"
                "try:\n"
                "    client.execute()\n"
                "except CellExecutionError as e:\n"
                "    if 'AssertionError' not in str(e):\n"
                "        raise\n"
                "nbformat.write(nb, 'submission.ipynb')\n"
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
            except ResourceLimitExceededException:
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
        # Оценка строится на подмене test-cell source:
        # ячейка студента исполняется, затем тестовая часть берется из tutor.ipynb.
        _scan_notebook_for_malicious_code(submission_content)
        with _workspace_context() as workspace:
            (workspace / "submission.ipynb").write_bytes(submission_content)
            (workspace / "tutor.ipynb").write_bytes(tutor_content)
            _write_resources(workspace, resources)

            script = (
                "import json\n"
                "import re\n"
                "import nbformat\n"
                "from nbclient import NotebookClient\n"
                "from nbclient.exceptions import CellExecutionError\n"
                "submission = nbformat.read('submission.ipynb', as_version=4)\n"
                "tutor = nbformat.read('tutor.ipynb', as_version=4)\n"
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
