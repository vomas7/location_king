#!/usr/bin/env python3
"""
Скрипт для добавления дополнительных игровых зон.
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
from app.models.location_zone import LocationZone
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Дополнительные игровые зоны
ADDITIONAL_ZONES = [
    # Европейские столицы (легко)
    {
        "name": "Париж, Франция",
        "description": "Столица Франции с узнаваемой радиальной планировкой и Сеной",
        "difficulty": 1,
        "category": "city",
        "polygon": "POLYGON((2.2 48.8, 2.2 48.9, 2.4 48.9, 2.4 48.8, 2.2 48.8))",
    },
    {
        "name": "Лондон, Великобритания",
        "description": "Столица Великобритании с Темзой и характерной планировкой",
        "difficulty": 1,
        "category": "city",
        "polygon": "POLYGON((-0.2 51.4, -0.2 51.6, 0.1 51.6, 0.1 51.4, -0.2 51.4))",
    },
    {
        "name": "Берлин, Германия",
        "description": "Столица Германии с рекой Шпрее и парком Тиргартен",
        "difficulty": 1,
        "category": "city",
        "polygon": "POLYGON((13.2 52.4, 13.2 52.6, 13.5 52.6, 13.5 52.4, 13.2 52.4))",
    },
    
    # Американские города
    {
        "name": "Нью-Йорк, США",
        "description": "Манхэттен с прямоугольной сеткой улиц и Центральным парком",
        "difficulty": 1,
        "category": "city",
        "polygon": "POLYGON((-74.1 40.6, -74.1 40.9, -73.9 40.9, -73.9 40.6, -74.1 40.6))",
    },
    {
        "name": "Лос-Анджелес, США",
        "description": "Город с характерной автомобильной инфраструктурой и холмами",
        "difficulty": 2,
        "category": "city",
        "polygon": "POLYGON((-118.4 33.9, -118.4 34.2, -118.1 34.2, -118.1 33.9, -118.4 33.9))",
    },
    
    # Азиатские города
    {
        "name": "Токио, Япония",
        "description": "Столица Японии с заливом и плотной застройкой",
        "difficulty": 2,
        "category": "city",
        "polygon": "POLYGON((139.6 35.5, 139.6 35.8, 139.9 35.8, 139.9 35.5, 139.6 35.5))",
    },
    {
        "name": "Пекин, Китай",
        "description": "Столица Китая с кольцевой структурой и Запретным городом",
        "difficulty": 2,
        "category": "city",
        "polygon": "POLYGON((116.2 39.8, 116.2 40.0, 116.5 40.0, 116.5 39.8, 116.2 39.8))",
    },
    
    # Природные объекты (сложно)
    {
        "name": "Гранд-Каньон, США",
        "description": "Один из самых глубоких каньонов в мире",
        "difficulty": 4,
        "category": "nature",
        "polygon": "POLYGON((-113.0 35.9, -113.0 36.3, -112.0 36.3, -112.0 35.9, -113.0 35.9))",
    },
    {
        "name": "Амазонка, Бразилия",
        "description": "Бассейн реки Амазонки с тропическими лесами",
        "difficulty": 5,
        "category": "nature",
        "polygon": "POLYGON((-70.0 -5.0, -70.0 0.0, -60.0 0.0, -60.0 -5.0, -70.0 -5.0))",
    },
    {
        "name": "Сахара, Африка",
        "description": "Крупнейшая пустыня в мире",
        "difficulty": 5,
        "category": "desert",
        "polygon": "POLYGON((-10.0 20.0, -10.0 30.0, 30.0 30.0, 30.0 20.0, -10.0 20.0))",
    },
    
    # Горные массивы
    {
        "name": "Альпы, Европа",
        "description": "Крупнейший горный массив Европы",
        "difficulty": 4,
        "category": "mountains",
        "polygon": "POLYGON((5.0 44.0, 5.0 48.0, 15.0 48.0, 15.0 44.0, 5.0 44.0))",
    },
    {
        "name": "Гималаи, Азия",
        "description": "Высочайшая горная система Земли",
        "difficulty": 5,
        "category": "mountains",
        "polygon": "POLYGON((80.0 27.0, 80.0 30.0, 90.0 30.0, 90.0 27.0, 80.0 27.0))",
    },
    
    # Острова и архипелаги
    {
        "name": "Гавайи, США",
        "description": "Вулканический архипелаг в Тихом океане",
        "difficulty": 3,
        "category": "islands",
        "polygon": "POLYGON((-160.0 18.0, -160.0 22.0, -154.0 22.0, -154.0 18.0, -160.0 18.0))",
    },
    {
        "name": "Мальдивы",
        "description": "Коралловый архипелаг в Индийском океане",
        "difficulty": 4,
        "category": "islands",
        "polygon": "POLYGON((72.0 -1.0, 72.0 7.0, 74.0 7.0, 74.0 -1.0, 72.0 -1.0))",
    },
    
    # Полярные регионы
    {
        "name": "Антарктида (побережье)",
        "description": "Побережье самого южного континента",
        "difficulty": 5,
        "category": "polar",
        "polygon": "POLYGON((-70.0 -70.0, -70.0 -65.0, -60.0 -65.0, -60.0 -70.0, -70.0 -70.0))",
    },
    
    # Исторические места
    {
        "name": "Долина Царей, Египет",
        "description": "Древнеегипетский некрополь близ Луксора",
        "difficulty": 3,
        "category": "historical",
        "polygon": "POLYGON((32.5 25.6, 32.5 25.8, 32.7 25.8, 32.7 25.6, 32.5 25.6))",
    },
    {
        "name": "Мачу-Пикчу, Перу",
        "description": "Древний город инков в Андах",
        "difficulty": 4,
        "category": "historical",
        "polygon": "POLYGON((-72.6 -13.2, -72.6 -13.1, -72.5 -13.1, -72.5 -13.2, -72.6 -13.2))",
    },
]


async def add_additional_zones():
    """Добавить дополнительные игровые зоны в базу данных"""
    logger.info("Adding additional location zones...")
    
    # Создаём engine и сессию
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            added_count = 0
            skipped_count = 0
            
            for zone_data in ADDITIONAL_ZONES:
                # Проверяем, существует ли уже зона с таким именем
                from sqlalchemy import select
                existing_stmt = select(LocationZone).where(
                    LocationZone.name == zone_data["name"]
                )
                existing_result = await session.execute(existing_stmt)
                existing_zone = existing_result.scalar_one_or_none()
                
                if existing_zone:
                    logger.info(f"Zone '{zone_data['name']}' already exists, skipping")
                    skipped_count += 1
                    continue
                
                # Создаём новую зону
                zone = LocationZone(
                    name=zone_data["name"],
                    description=zone_data["description"],
                    difficulty=zone_data["difficulty"],
                    category=zone_data["category"],
                    polygon=WKTElement(zone_data["polygon"], srid=4326),
                    is_active=True,
                )
                
                session.add(zone)
                added_count += 1
                logger.info(f"Added zone: {zone_data['name']} (difficulty: {zone_data['difficulty']})")
            
            await session.commit()
            
            logger.info(f"\n=== Summary ===")
            logger.info(f"Added: {added_count} new zones")
            logger.info(f"Skipped: {skipped_count} existing zones")
            logger.info(f"Total zones in database: {added_count + skipped_count}")
            
            # Выводим статистику по категориям
            from sqlalchemy import func
            
            stats_stmt = select(
                LocationZone.category,
                func.count(LocationZone.id).label("count"),
                func.avg(LocationZone.difficulty).label("avg_difficulty")
            ).where(
                LocationZone.is_active == True
            ).group_by(LocationZone.category)
            
            stats_result = await session.execute(stats_stmt)
            stats = stats_result.all()
            
            logger.info(f"\n=== Zones by category ===")
            for category, count, avg_diff in stats:
                logger.info(f"{category or 'No category'}: {count} zones, avg difficulty: {avg_diff:.1f}")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error adding zones: {e}")
            raise
        finally:
            await session.close()
    
    await engine.dispose()


async def list_all_zones():
    """Вывести список всех зон в базе"""
    logger.info("Listing all location zones...")
    
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            from sqlalchemy import select
            
            stmt = select(LocationZone).where(
                LocationZone.is_active == True
            ).order_by(LocationZone.difficulty, LocationZone.name)
            
            result = await session.execute(stmt)
            zones = result.scalars().all()
            
            logger.info(f"\n=== All Active Location Zones ({len(zones)} total) ===")
            for zone in zones:
                logger.info(f"ID: {zone.id:3d} | {zone.name:30s} | "
                          f"Difficulty: {zone.difficulty}/5 | "
                          f"Category: {zone.category or 'N/A':15s}")
                
        except Exception as e:
            logger.error(f"Error listing zones: {e}")
        finally:
            await session.close()
    
    await engine.dispose()


if __name__ == "__main__":
    # Проверяем, что настройки загружены
    if not settings.database_url:
        logger.error("DATABASE_URL not set in environment or .env file")
        sys.exit(1)
    
    # Запускаем добавление зон
    asyncio.run(add_additional_zones())
    
    # Выводим список всех зон
    asyncio.run(list_all_zones())