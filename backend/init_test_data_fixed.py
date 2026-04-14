#!/usr/bin/env python3
"""
Инициализация тестовых данных для Location King.
Исправленная версия с правильным UUID.
"""
import asyncio
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.user import User
from app.models.location_zone import LocationZone
from app.models.game_session import GameSession
from app.models.round import Round
from app.config import settings

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_database():
    """Инициализировать базу данных тестовыми данными"""
    logger.info("Initializing database with test data...")
    
    # Создаём движок
    engine = create_async_engine(settings.database_url, echo=False)
    
    # Создаём сессию
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    try:
        async with async_session() as session:
            # Проверяем, есть ли уже данные
            result = await session.execute(select(LocationZone))
            zones = result.scalars().all()
            
            if zones:
                logger.info(f"Database already has {len(zones)} zones. Skipping initialization.")
                return
            
            # Создаём тестового пользователя с правильным UUID
            test_user = User(
                keycloak_id=uuid.uuid4(),  # Генерируем случайный UUID
                username="test_player",
                email="test@example.com",
                display_name="Тестовый игрок",
                total_score=0,
                games_played=0,
                games_won=0,
                total_rounds=0,
                average_score=None,
                average_distance=None,
                best_score=0,
                worst_score=0,
                elo_rating=1000,
                rank=None,
                level=1,
                experience=0,
                avatar_url=None,
                bio="Тестовый аккаунт для разработки",
                country="Россия",
                timezone="Europe/Moscow",
                language="ru",
                is_active=True,
                is_verified=False,
                is_premium=False,
                email_verified=False,
                updated_at=datetime.utcnow(),
                last_login_at=datetime.utcnow(),
                last_activity_at=datetime.utcnow()
            )
            
            session.add(test_user)
            await session.flush()  # Получаем ID пользователя
            
            logger.info(f"Created test user: {test_user.username} (ID: {test_user.id})")
            
            # Создаём тестовые зоны (упрощённые полигоны)
            test_zones = [
                {
                    "name": "Москва, центр",
                    "description": "Центральный район Москвы вокруг Кремля",
                    "difficulty": 2,
                    "category": "urban",
                    "polygon": "POLYGON((37.6 55.75, 37.65 55.75, 37.65 55.77, 37.6 55.77, 37.6 55.75))",
                    "center_point": "POINT(37.617 55.755)",
                    "country": "Россия",
                    "region": "Москва",
                    "tags": "столица,город,история"
                },
                {
                    "name": "Санкт-Петербург, центр",
                    "description": "Исторический центр Санкт-Петербурга",
                    "difficulty": 3,
                    "category": "urban",
                    "polygon": "POLYGON((30.3 59.93, 30.35 59.93, 30.35 59.95, 30.3 59.95, 30.3 59.93))",
                    "center_point": "POINT(30.315 59.939)",
                    "country": "Россия",
                    "region": "Санкт-Петербург",
                    "tags": "северная столица,каналы,архитектура"
                },
                {
                    "name": "Сочи, побережье",
                    "description": "Черноморское побережье в Сочи",
                    "difficulty": 4,
                    "category": "coastal",
                    "polygon": "POLYGON((39.7 43.57, 39.75 43.57, 39.75 43.6, 39.7 43.6, 39.7 43.57))",
                    "center_point": "POINT(39.73 43.585)",
                    "country": "Россия",
                    "region": "Краснодарский край",
                    "tags": "курорт,море,горы"
                },
                {
                    "name": "Озеро Байкал",
                    "description": "Южная часть озера Байкал",
                    "difficulty": 5,
                    "category": "natural",
                    "polygon": "POLYGON((106.5 51.8, 107.5 51.8, 107.5 52.0, 106.5 52.0, 106.5 51.8))",
                    "center_point": "POINT(107.0 51.9)",
                    "country": "Россия",
                    "region": "Иркутская область",
                    "tags": "озеро,природа,глубина"
                },
                {
                    "name": "Пустыня Гоби",
                    "description": "Центральная часть пустыни Гоби",
                    "difficulty": 6,
                    "category": "desert",
                    "polygon": "POLYGON((102.0 44.0, 104.0 44.0, 104.0 45.0, 102.0 45.0, 102.0 44.0))",
                    "center_point": "POINT(103.0 44.5)",
                    "country": "Монголия",
                    "region": "Гоби",
                    "tags": "пустыня,пески,экстремально"
                },
                {
                    "name": "Центральная Европа",
                    "description": "Горный район в Центральной Европе",
                    "difficulty": 4,
                    "category": "mountain",
                    "polygon": "POLYGON((11.0 47.0, 12.0 47.0, 12.0 48.0, 11.0 48.0, 11.0 47.0))",
                    "center_point": "POINT(11.5 47.5)",
                    "country": "Австрия",
                    "region": "Тироль",
                    "tags": "горы,альпы,лыжи"
                }
            ]
            
            zones_created = []
            for zone_data in test_zones:
                zone = LocationZone(
                    name=zone_data["name"],
                    description=zone_data["description"],
                    difficulty=zone_data["difficulty"],
                    category=zone_data["category"],
                    polygon=zone_data["polygon"],
                    center_point=zone_data["center_point"],
                    area_sq_km=100.0,  # Примерная площадь
                    total_rounds=0,
                    average_score=None,
                    average_distance=None,
                    popularity=0,
                    country=zone_data["country"],
                    region=zone_data["region"],
                    tags=zone_data["tags"],
                    thumbnail_url=None,
                    is_featured=True,
                    is_premium=False,
                    is_active=True,
                    updated_at=datetime.utcnow()
                )
                session.add(zone)
                zones_created.append(zone)
            
            await session.commit()
            
            logger.info(f"Created {len(zones_created)} test zones")
            
            # Создаём тестовую игровую сессию
            test_session = GameSession(
                user_id=test_user.id,
                mode="solo",
                status="active",
                rounds_total=5,
                rounds_done=0,
                total_score=0,
                time_control="unlimited",
                average_score=None,
                best_round_score=0,
                worst_round_score=0,
                title="Тестовая игра",
                description="Первая тестовая игровая сессия",
                is_public=True,
                allow_comments=True,
                started_at=datetime.utcnow(),
                last_activity_at=datetime.utcnow()
            )
            
            session.add(test_session)
            await session.commit()
            
            logger.info(f"Created test game session: {test_session.id}")
            
            logger.info("Database initialization completed successfully!")
            
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_database())