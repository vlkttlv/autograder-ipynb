import subprocess
from pathlib import Path

import pytest

from app.exceptions import SandboxExecutionException
from app.submissions.services.sandbox_runner import _docker_mount_source, _run_in_container, _write_resources


def test_run_in_container_builds_docker_command(monkeypatch, tmp_path: Path):
    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    _run_in_container(["python", "-V"], tmp_path, 30)

    assert captured["cmd"][:4] == ["docker", "run", "--rm", "--network"]
    mount_arg = next(arg for arg in captured["cmd"] if arg.startswith("type=bind,"))
    assert "target=/workspace" in mount_arg
    assert captured["cmd"][-2:] == ["python", "-V"]


def test_run_in_container_raises_on_missing_docker(tmp_path: Path, monkeypatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("docker not found")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(SandboxExecutionException):
        _run_in_container(["python", "-V"], tmp_path, 30)


def test_docker_mount_source_windows_path():
    class FakePath:
        def resolve(self):
            return "C:\\Users\\student\\AppData\\Local\\Temp\\tmp123"

    assert _docker_mount_source(FakePath()) == "/host_mnt/c/Users/student/AppData/Local/Temp/tmp123"


def test_write_resources_keeps_subdirectories(tmp_path: Path):
    resources = [("data/config/settings.json", b"{}"), ("../unsafe.txt", b"x")]

    _write_resources(tmp_path, resources)

    assert (tmp_path / "data" / "config" / "settings.json").read_bytes() == b"{}"
    assert not (tmp_path / "unsafe.txt").exists()


def test_execute_notebook_maps_dead_kernel_to_resource_limit(monkeypatch):
    import subprocess

    import pytest

    from app.exceptions import ResourceLimitExceededException, SandboxExecutionException
    from app.submissions.services.sandbox_runner import SandboxNotebookRunner

    err = subprocess.CalledProcessError(1, ["docker"], stderr="nbclient.exceptions.DeadKernelError: Kernel died")

    def fake_run(*args, **kwargs):
        raise SandboxExecutionException from err

    monkeypatch.setattr("app.submissions.services.sandbox_runner._run_in_container", fake_run)

    with pytest.raises(ResourceLimitExceededException):
        SandboxNotebookRunner.execute_notebook(b"{}", [], timeout_seconds=30)
