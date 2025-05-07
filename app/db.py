from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy import NullPool, Pool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.config import settings

if settings.MODE == "TEST":
    DATABASE_URL = settings.TEST_DATABASE_URL
    DATABASE_PARAMS = {'poolclass': NullPool}
else:
    DATABASE_URL = settings.DATABASE_URL
    DATABASE_PARAMS = {
        'pool_size': 10,  # количество соединений в пуле
        'max_overflow': 20,  # максимальное количество соединений, которое может быть создано при превышении pool_size
        'pool_timeout': 30,  # время ожидания, чтобы получить соединение из пула
        'pool_recycle': 3600  # время, через которое соединения будут сбрасываться
    }

engine = create_async_engine(DATABASE_URL, **DATABASE_PARAMS)  

async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass
