# Автогрейдер ipynb файлов

## Клонируйте репозиторий
```
git clone https://github.com/vlkttlv/autograder-ipynb.git
cd autograder-ipynb
```
## Активация виртуального окружения
В командной строке ввести:
```
python -m venv venv
```
```
venv\Scripts\activate 
```
или для linux/mac

```
source venv/bin/activate 
```
## Установка зависимостей

```
pip install -r requirements.txt
```

## Переменные окружения
(корень проекта) - создать файл .env (или .env-docker для запуска через Docker)

```
MODE=DEV

DB_HOST=localhost
DB_PORT=5432
DB_USER=db_user
DB_PASS=db_password
DB_NAME=db_name

TEST_DB_HOST=localhost
TEST_DB_PORT=5432
TEST_DB_USER=test_db_user
TEST_DB_PASS=test_db_password
TEST_DB_NAME=test_db_name

SECRET_KEY=12345qwerty
ALGORITHM=HS256

POSTGRES_DB=autograder
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

GOOGLE_REDIRECT_URI=your_redirect_api
CLIENT_SECRETS_FILE=path_to_secret_file

DROPBOX_REFRESH_TOKEN=your_token
DROPBOX_APP_KEY=your_app_key
DROPBOX_APP_SECRET=your_app_secret
```

!!! В postgres должна быть создана БД
## Запуск через Docker
```bash
docker-compose up --build
```
Приложение доступно по адресу: ```http://localhost:8000```

## Запуск локально
### Миграции

В командной строке ввести:
```bash
alembic upgrade head
```

### Запуск приложения

```
uvicorn app.main:app --reload
```
Приложение доступно по адресу: ```http://127.0.0.1:8000```

## Изоляция выполнения кода студентов (рекомендуемый вариант)
Реализован **Вариант 1: Docker-контейнер на каждый запуск**.

### Что происходит
- При загрузке решения и при проверке запускается отдельный `docker run --rm`.
- В контейнер монтируется только временная папка с `ipynb` и ресурсами задания.
- Контейнер запускается с ограничениями (`--network none`, CPU/RAM/PIDs limits, `--cap-drop ALL`, `no-new-privileges`).
- После завершения проверки контейнер удаляется автоматически (`--rm`).

### Переменные окружения для sandbox
Добавьте в `.env`:

```env
SANDBOX_DOCKER_IMAGE=autograder-ipynb:latest
SANDBOX_CPU_LIMIT=1
SANDBOX_MEMORY_LIMIT=512m
SANDBOX_PIDS_LIMIT=256
```

Лимит на выполнение ноутбука теперь задается преподавателем в самом задании (в секундах).

### Как подготовить образ для sandbox
Нужен Docker-образ, внутри которого установлены зависимости из `requirements.txt` и доступен Python kernel.

Пример:
```bash
docker build -t autograder-ipynb:latest .
```

### Нужны ли ключи?
Для sandbox на Docker **дополнительные ключи не нужны**.
Нужен только установленный Docker daemon и доступ процесса приложения к `docker` CLI.

Секреты типа `DROPBOX_*` и Google OAuth берутся так же, как и раньше:
- `DROPBOX_REFRESH_TOKEN`, `DROPBOX_APP_KEY`, `DROPBOX_APP_SECRET` — из вашего Dropbox App в [Dropbox Developers].
- `CLIENT_SECRETS_FILE`, `GOOGLE_REDIRECT_URI` — из Google Cloud Console (OAuth credentials).


### Если в логах `DeadKernelError: Kernel died`
Это обычно означает, что код студента превысил лимиты контейнера (чаще всего память/CPU) или процесс ядра был аварийно завершен.

Что сделать:
- увеличьте `SANDBOX_MEMORY_LIMIT` (например, до `1g` или `2g`),
- увеличьте лимит времени проверки в настройках конкретного задания,
- убедитесь, что образ `SANDBOX_DOCKER_IMAGE` содержит все нужные зависимости задания.
