import os
import re

c = get_config()  # noqa: F821

public_base = os.getenv("JUPYTERHUB_PUBLIC_BASE_URL", "/jhub")
app_origin = os.getenv("APP_ORIGIN", "http://localhost:8000")

if not public_base.startswith("/"):
    public_base = f"/{public_base}"

public_base = public_base.rstrip("/") + "/"

c.JupyterHub.bind_url = f"http://:8000{public_base}"
c.JupyterHub.hub_ip = "0.0.0.0"
c.JupyterHub.hub_connect_ip = "jupyterhub"
c.JupyterHub.db_url = "sqlite:////srv/jupyterhub/data/jupyterhub.sqlite"
c.JupyterHub.tornado_settings = {
    "headers": {
        "Content-Security-Policy": f"frame-ancestors 'self' {app_origin}",
        "X-Frame-Options": "SAMEORIGIN",
    }
}

c.JupyterHub.authenticator_class = "dummy"
c.DummyAuthenticator.password = os.getenv("JUPYTERHUB_DUMMY_PASSWORD", "")
# Включаем named servers: отдельный сервер на каждое задание студента
c.JupyterHub.allow_named_servers = True
c.JupyterHub.named_server_limit_per_user = 100

c.JupyterHub.spawner_class = "dockerspawner.DockerSpawner"
c.DockerSpawner.image = "autograder-ipynb:latest"
c.Spawner.cmd = ["jupyterhub-singleuser"]
c.DockerSpawner.extra_create_kwargs = {"user": "1000"}
c.DockerSpawner.remove = True
c.DockerSpawner.network_name = os.getenv("DOCKER_NETWORK_NAME", "autograder_default")
c.DockerSpawner.notebook_dir = "/home/jovyan/work"
c.DockerSpawner.default_url = "/lab"
c.Spawner.args = [
    f"--ServerApp.tornado_settings={{\"headers\":{{\"Content-Security-Policy\":\"frame-ancestors 'self' {app_origin}\"}}}}"
]


def _safe_name(value: str) -> str:
    """Нормализует имя для безопасного использования в имени Docker volume"""
    safe = re.sub(r"[^a-z0-9-]", "-", value.lower())
    return safe.strip("-")[:120] or "srv"


async def _per_assignment_volume(spawner):
    """Для каждого задания (сервера) создаем отдельный volume,
    чтобы студент не видел файлы из других заданий"""
    username = _safe_name(spawner.user.name)
    server_name = _safe_name(spawner.name or "default")
    volume_name = f"jhub-{username}-{server_name}"
    spawner.volumes = {volume_name: "/home/jovyan/work"}
    spawner.notebook_dir = "/home/jovyan/work"


c.Spawner.pre_spawn_hook = _per_assignment_volume

c.JupyterHub.services = [
    {
        "name": "autograder-backend",
        "api_token": os.getenv("JUPYTERHUB_ADMIN_TOKEN", ""),
        "admin": True,
    }
]

# JupyterHub 5 RBAC: права backend-сервису на управление
# пользователями, серверами и токенами.
c.JupyterHub.load_roles = [
    {
        "name": "autograder-backend-role",
        "description": "Permissions for autograder backend integration",
        "services": ["autograder-backend"],
        "scopes": [
            "read:users",
            "list:users",
            "admin:users",
            "read:servers",
            "admin:servers",
            "tokens",
        ],
    }
]
