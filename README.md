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
