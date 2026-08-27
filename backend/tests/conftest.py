"""
Общая обвязка тестов.

Схема тестовой базы поднимается миграциями Alembic — так проверяется ещё и то,
что миграции накатываются на пустую базу. Каждый тест выполняется во вложенной
транзакции, которая откатывается после него, поэтому тесты не видят друг друга.
"""

import os
from collections.abc import AsyncGenerator

import pytest
from alembic import command
from alembic.config import Config
from geoalchemy2 import WKTElement
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import get_db
from app.main import app
from app.models.location_zone import LocationZone
from app.models.user import User
from app.services.auth import register

TEST_DATABASE_URL = os.environ["DATABASE_URL"]

# Квадрат примерно 20 на 20 км под Москвой
TEST_POLYGON = "POLYGON((37.5 55.6, 37.5 55.8, 37.8 55.8, 37.8 55.6, 37.5 55.6))"


@pytest.fixture(scope="session")
def migrated_database() -> None:
    """Накатить миграции на тестовую базу один раз за прогон."""
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

    command.downgrade(config, "base")
    command.upgrade(config, "head")


@pytest.fixture
async def db(migrated_database: None) -> AsyncGenerator[AsyncSession, None]:
    """Сессия БД в транзакции, которая откатывается после теста."""
    engine = create_async_engine(TEST_DATABASE_URL)

    async with engine.connect() as connection:
        transaction = await connection.begin()
        factory = async_sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        async with factory() as session:
            yield session

        await transaction.rollback()

    await engine.dispose()


@pytest.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP-клиент поверх ASGI-приложения с общей транзакцией теста."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as http_client:
        yield http_client

    app.dependency_overrides.clear()


@pytest.fixture
async def zone(db: AsyncSession) -> LocationZone:
    """Одна активная зона, чтобы раунду было из чего выбирать точку."""
    zone = LocationZone(
        name="Тестовая зона",
        description="Квадрат под Москвой",
        difficulty=1,
        category="city",
        country="Россия",
        polygon=WKTElement(TEST_POLYGON, srid=4326),
        is_active=True,
    )
    db.add(zone)
    await db.flush()
    return zone


@pytest.fixture
async def guest(client: AsyncClient) -> dict:
    """Гость и его токены."""
    response = await client.post("/api/auth/guest")
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def auth_headers(guest: dict) -> dict[str, str]:
    """Заголовок авторизации гостя."""
    return {"Authorization": f"Bearer {guest['tokens']['access_token']}"}


@pytest.fixture
async def other_user_headers(client: AsyncClient) -> dict[str, str]:
    """Заголовок авторизации второго игрока — для проверок чужого доступа."""
    response = await client.post("/api/auth/guest")
    return {"Authorization": f"Bearer {response.json()['tokens']['access_token']}"}


@pytest.fixture
async def registered_user(db: AsyncSession) -> User:
    """Пользователь с паролем."""
    user = await register(db, "player@example.com", "correct horse battery", "Игрок")
    await db.flush()
    return user
