import logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

LOG_FILE = "app/logs/autograder.log"


def configure_logging():
    """
    Настройка логирования для всего проекта:
    - консоль
    - файл с ротацией
    - формат с временем, именем логгера и уровнем
    """
    # Формат для логов
    formatter = logging.Formatter(
        "%(levelname)s - %(asctime)s - %(name)s - %(message)s"
    )

    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Файловый обработчик с ротацией (5 МБ на файл, 5 резервных файлов)
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    # Конфигурация корневого логгера
    logging.basicConfig(
        level=logging.INFO,
        handlers=[console_handler, file_handler],
    )

    logging.getLogger("asyncio").setLevel(logging.WARNING)
    # logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def setup_fastapi_exception_logging(app: FastAPI):
    """
    Middleware для логирования всех необработанных ошибок FastAPI
    """
    logger = logging.getLogger("fastapi")

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(
            f"Ошибка при запросе {request.method} {request.url}: {exc}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )
