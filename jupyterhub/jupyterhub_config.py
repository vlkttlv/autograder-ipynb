import os
import re
from tornado import web
from jupyterhub.auth import Authenticator
from jupyterhub.handlers import BaseHandler


c = get_config()

public_base = os.getenv("JUPYTERHUB_PUBLIC_BASE_URL", "/jhub")
app_origin = os.getenv("APP_ORIGIN", "http://localhost:8000")

if not public_base.startswith("/"):
    public_base = f"/{public_base}"

public_base = public_base.rstrip("/") + "/"

c.JupyterHub.bind_url = f"http://:8000{public_base}"

# IP, на котором hub доступен внутри сети Docker
c.JupyterHub.hub_ip = "0.0.0.0"
# IP, который контейнеры будут использовать для подключения к hub
c.JupyterHub.hub_connect_ip = "jupyterhub"

# База данных JupyterHub
c.JupyterHub.db_url = "sqlite:////srv/jupyterhub/data/jupyterhub.sqlite"

# Настройки Tornado для заголовков безопасности
c.JupyterHub.tornado_settings = {
    "headers": {
        # CSP запрещает встраивание в другие домены кроме self и app_origin
        "Content-Security-Policy": f"frame-ancestors 'self' {app_origin}",
        "X-Frame-Options": "SAMEORIGIN",
    }
}

# Header-based auth via app session (nginx auth_request + X-Remote-User).
class HeaderAuthenticator(Authenticator):
    async def authenticate(self, handler, data=None):
        username = handler.request.headers.get("X-Remote-User")
        if not username:
            return None
        return {"name": username}

    def login_url(self, base_url):
        return f"{base_url}auto_login"


class AutoLoginHandler(BaseHandler):
    async def get(self):
        user = await self.login_user(data=None)
        if not user:
            raise web.HTTPError(403)
        next_url = self.get_argument("next", self.base_url)
        self.redirect(next_url)


c.JupyterHub.authenticator_class = HeaderAuthenticator
c.Authenticator.auto_login = True
c.Authenticator.allow_all = True
c.Authenticator.any_allow_config = True
c.JupyterHub.extra_handlers = [
    (r"/auto_login", AutoLoginHandler),
    (r"/login", AutoLoginHandler),
]

# Разрешаем создание нескольких серверов на одного пользователя
c.JupyterHub.allow_named_servers = True
# Ограничиваем до 100 серверов на одного пользователя
c.JupyterHub.named_server_limit_per_user = 100

# Спавнер Docker — запускаем каждого пользователя в отдельном контейнере
c.JupyterHub.spawner_class = "dockerspawner.DockerSpawner"
c.DockerSpawner.image = "autograder-ipynb:latest" # Образ контейнера для пользователя
c.Spawner.cmd = ["jupyterhub-singleuser"] # Команда запуска Jupyter внутри контейнера
c.DockerSpawner.extra_create_kwargs = {"user": "1000"} # Запуск контейнера от непривилегированного пользователя
c.DockerSpawner.remove = True # Удаляем контейнер при остановке
c.DockerSpawner.network_name = os.getenv("DOCKER_NETWORK_NAME", "autograder_default") # Сеть Docker для контейнеров пользователей
c.DockerSpawner.notebook_dir = "/home/jovyan/work" # Рабочая директория внутри контейнера
c.DockerSpawner.default_url = "/lab" # URL по умолчанию для пользователя (JupyterLab)
# Передаем CSP каждому серверу через аргументы запуска
c.Spawner.args = [
    f"--ServerApp.tornado_settings={{\"headers\":{{\"Content-Security-Policy\":\"frame-ancestors 'self' {app_origin}\"}}}}"
]


def _safe_name(value: str) -> str:
    """Функция нормализации имени пользователя/сервера для безопасного использования в имени Docker volume"""
    safe = re.sub(r"[^a-z0-9-]", "-", value.lower())
    return safe.strip("-")[:120] or "srv"


async def _per_assignment_volume(spawner):
    """Cоздаёт отдельный volume на каждый сервер"""
    username = _safe_name(spawner.user.name)
    server_name = _safe_name(spawner.name or "default")
    volume_name = f"jhub-{username}-{server_name}"
    spawner.volumes = {volume_name: "/home/jovyan/work"}
    spawner.notebook_dir = "/home/jovyan/work"

# Устанавливаем pre_spawn_hook для spawner
c.Spawner.pre_spawn_hook = _per_assignment_volume

c.JupyterHub.services = [
    {
        "name": "autograder-backend",
        "api_token": os.getenv("JUPYTERHUB_ADMIN_TOKEN", ""),
        "admin": True,  # сервис имеет права администратора
    }
]

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
