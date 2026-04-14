#!/usr/bin/env python3
"""
Скрипт для инициализации тестовых данных в базе.
Создаёт тестовые игровые зоны и пользователя.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from geoalchemy2 import WKTElement

from app.database import Base
from app.models.user import User
from app.models.location_zone import LocationZone
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_database():
    """Инициализировать базу данных тестовыми данными"""
    logger.info("Initializing database with test data...")
    
    # Создаём engine и сессию
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        # Создаём таблицы (если их ещё нет)
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        try:
            # 1. Создаём тестового пользователя
            test_user = User(
                keycloak_id="test-user-123",
                username="test_player",
                total_score=0,
            )
            session.add(test_user)
            await session.flush()
            logger.info(f"Created test user: {test_user.username} (ID: {test_user.id})")
            
            # 2. Создаём тестовые игровые зоны
            
            # Москва (легко)
            moscow_zone = LocationZone(
                name="Москва, центр",
                description="Центральная часть Москвы с узнаваемой радиально-кольцевой структурой",
                difficulty=1,
                category="city",
                polygon=WKTElement(
                    "POLYGON((37.3 55.6, 37.3 55.9, 38.0 55.9, 38.0 55.6, 37.3 55.6))",
                    srid=4326
                ),
                is_active=True,
            )
            session.add(moscow_zone)
            
            # Санкт-Петербург (легко)
            spb_zone = LocationZone(
                name="Санкт-Петербург",
                description="Исторический центр Санкт-Петербурга с Невой и каналами",
                difficulty=1,
                category="city",
                polygon=WKTElement(
                    "POLYGON((30.0 59.8, 30.0 60.1, 30.5 60.1, 30.5 59.8, 30.0 59.8))",
                    srid=4326
                ),
                is_active=True,
            )
            session.add(spb_zone)
            
            # Сочи (средне)
            sochi_zone = LocationZone(
                name="Сочи, побережье",
                description="Черноморское побережье Сочи с горными массивами",
                difficulty=2,
                category="coast",
                polygon=WKTElement(
                    "POLYGON((39.5 43.4, 39.5 43.7, 40.0 43.7, 40.0 43.4, 39.5 43.4))",
                    srid=4326
                ),
                is_active=True,
            )
            session.add(sochi_zone)
            
            # Байкал (сложно)
            baikal_zone = LocationZone(
                name="Озеро Байкал",
                description="Котловина озера Байкал - самое глубокое озеро в мире",
                difficulty=4,
                category="nature",
                polygon=WKTElement(
                    "POLYGON((103.0 51.0, 103.0 56.0, 110.0 56.0, 110.0 51.0, 103.0 51.0))",
                    srid=4326
                ),
                is_active=True,
            )
            session.add(baikal_zone)
            
            # Пустыня Гоби (очень сложно)
            gobi_zone = LocationZone(
                name="Пустыня Гоби",
                description="Обширная пустынная область в Центральной Азии",
                difficulty=5,
                category="desert",
                polygon=WKTElement(
                    "POLYGON((90.0 40.0, 90.0 45.0, 110.0 45.0, 110.0 40.0, 90.0 40.0))",
                    srid=4326
                ),
                is_active=True,
            )
            session.add(gobi_zone)
            
            # Европа (разные типы местности)
            europe_zone = LocationZone(
                name="Центральная Европа",
                description="Разнообразные ландшафты Центральной Европы",
                difficulty=3,
                category="mixed",
                polygon=WKTElement(
                    "POLYGON((5.0 45.0, 5.0 55.0, 15.0 55.0, 15.0 45.0, 5.0 45.0))",
                    srid=4326
                ),
                is_active=True,
            )
            session.add(europe_zone)
            
            await session.commit()
            logger.info("Created 6 test location zones")
            
            # 3. Выводим информацию о созданных данных
            zones_result = await session.execute(
                "SELECT id, name, difficulty, ST_AsText(polygon) as polygon FROM location_zones"
            )
            zones = zones_result.fetchall()
            
            logger.info("\n=== Created Location Zones ===")
            for zone in zones:
                logger.info(f"ID: {zone.id}, Name: {zone.name}, Difficulty: {zone.difficulty}")
                logger.info(f"  Polygon: {zone.polygon[:80]}...")
            
            logger.info("\nDatabase initialization completed successfully!")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error initializing database: {e}")
            raise
        finally:
            await session.close()
    
    await engine.dispose()


if __name__ == "__main__":
    # Проверяем, что настройки загружены
    if not settings.database_url:
        logger.error("DATABASE_URL not set in environment or .env file")
        sys.exit(1)
    
    # Запускаем инициализацию
    asyncio.run(init_database())