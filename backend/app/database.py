"""Подключение к PostgreSQL и базовый класс моделей."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Пул считается на один процесс, а процессов у приложения столько, сколько
# воркеров у uvicorn. Прежние 10 + 20 на четыре воркера давали до ста двадцати
# соединений при сотне разрешённых в PostgreSQL — под нагрузкой часть запросов
# просто получала бы отказ базы.
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_pool_overflow,
    pool_pre_ping=True,
    pool_recycle=1800,
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Сессия БД на время запроса: коммит при успехе, откат при ошибке."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
