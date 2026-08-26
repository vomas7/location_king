#!/usr/bin/env python3
"""
Загрузка игровых зон в базу.

Запускается сколько угодно раз: зоны сопоставляются по имени, существующие
обновляются, новые добавляются. Ничего не удаляет.

    python scripts/seed.py
    python scripts/seed.py --only-new
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from geoalchemy2 import WKTElement
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.location_zone import LocationZone

logger = logging.getLogger("seed")

ZONES = [
    {
        "name": "Москва, центр",
        "description": "Центральная часть Москвы с узнаваемой радиально-кольцевой структурой",
        "difficulty": 1,
        "category": "city",
        "country": "Россия",
        "region": "Москва",
        "tags": ["столица", "кольца"],
        "polygon": "POLYGON((37.3 55.6, 37.3 55.9, 38.0 55.9, 38.0 55.6, 37.3 55.6))",
    },
    {
        "name": "Санкт-Петербург",
        "description": "Исторический центр с Невой, каналами и прямоугольной планировкой",
        "difficulty": 1,
        "category": "city",
        "country": "Россия",
        "region": "Санкт-Петербург",
        "tags": ["каналы", "Нева"],
        "polygon": "POLYGON((30.0 59.8, 30.0 60.1, 30.5 60.1, 30.5 59.8, 30.0 59.8))",
    },
    {
        "name": "Сочи, побережье",
        "description": "Черноморское побережье, зажатое между морем и горными хребтами",
        "difficulty": 2,
        "category": "coast",
        "country": "Россия",
        "region": "Краснодарский край",
        "tags": ["море", "горы"],
        "polygon": "POLYGON((39.5 43.4, 39.5 43.7, 40.0 43.7, 40.0 43.4, 39.5 43.4))",
    },
    {
        "name": "Озеро Байкал",
        "description": "Котловина самого глубокого озера в мире",
        "difficulty": 4,
        "category": "nature",
        "country": "Россия",
        "region": "Прибайкалье",
        "tags": ["озеро", "тайга"],
        "polygon": "POLYGON((103.0 51.0, 103.0 56.0, 110.0 56.0, 110.0 51.0, 103.0 51.0))",
    },
    {
        "name": "Пустыня Гоби",
        "description": "Обширная пустынная область в Центральной Азии",
        "difficulty": 5,
        "category": "desert",
        "country": "Монголия",
        "region": "Гоби",
        "tags": ["пустыня", "степь"],
        "polygon": "POLYGON((90.0 40.0, 90.0 45.0, 110.0 45.0, 110.0 40.0, 90.0 40.0))",
    },
    {
        "name": "Центральная Европа",
        "description": "Разнообразные ландшафты между Альпами и Балтикой",
        "difficulty": 3,
        "category": "mixed",
        "country": "Германия",
        "region": "Центральная Европа",
        "tags": ["поля", "города"],
        "polygon": "POLYGON((5.0 45.0, 5.0 55.0, 15.0 55.0, 15.0 45.0, 5.0 45.0))",
    },
    {
        "name": "Париж, Франция",
        "description": "Столица Франции с узнаваемой радиальной планировкой и Сеной",
        "difficulty": 1,
        "category": "city",
        "country": "Франция",
        "region": "Иль-де-Франс",
        "tags": ["столица", "Сена"],
        "polygon": "POLYGON((2.2 48.8, 2.2 48.9, 2.4 48.9, 2.4 48.8, 2.2 48.8))",
    },
    {
        "name": "Лондон, Великобритания",
        "description": "Столица Великобритании с Темзой и характерной планировкой",
        "difficulty": 1,
        "category": "city",
        "country": "Великобритания",
        "region": "Большой Лондон",
        "tags": ["столица", "Темза"],
        "polygon": "POLYGON((-0.2 51.4, -0.2 51.6, 0.1 51.6, 0.1 51.4, -0.2 51.4))",
    },
    {
        "name": "Берлин, Германия",
        "description": "Столица Германии с рекой Шпрее и парком Тиргартен",
        "difficulty": 1,
        "category": "city",
        "country": "Германия",
        "region": "Берлин",
        "tags": ["столица", "Шпрее"],
        "polygon": "POLYGON((13.2 52.4, 13.2 52.6, 13.5 52.6, 13.5 52.4, 13.2 52.4))",
    },
    {
        "name": "Нью-Йорк, США",
        "description": "Манхэттен с прямоугольной сеткой улиц и Центральным парком",
        "difficulty": 1,
        "category": "city",
        "country": "США",
        "region": "Нью-Йорк",
        "tags": ["Манхэттен", "сетка улиц"],
        "polygon": "POLYGON((-74.1 40.6, -74.1 40.9, -73.9 40.9, -73.9 40.6, -74.1 40.6))",
    },
    {
        "name": "Лос-Анджелес, США",
        "description": "Город с характерной автомобильной инфраструктурой и холмами",
        "difficulty": 2,
        "category": "city",
        "country": "США",
        "region": "Калифорния",
        "tags": ["холмы", "хайвеи"],
        "polygon": "POLYGON((-118.4 33.9, -118.4 34.2, -118.1 34.2, -118.1 33.9, -118.4 33.9))",
    },
    {
        "name": "Токио, Япония",
        "description": "Столица Японии с заливом и плотной застройкой",
        "difficulty": 2,
        "category": "city",
        "country": "Япония",
        "region": "Канто",
        "tags": ["столица", "залив"],
        "polygon": "POLYGON((139.6 35.5, 139.6 35.8, 139.9 35.8, 139.9 35.5, 139.6 35.5))",
    },
    {
        "name": "Пекин, Китай",
        "description": "Столица Китая с кольцевой структурой и Запретным городом",
        "difficulty": 2,
        "category": "city",
        "country": "Китай",
        "region": "Пекин",
        "tags": ["столица", "кольца"],
        "polygon": "POLYGON((116.2 39.8, 116.2 40.0, 116.5 40.0, 116.5 39.8, 116.2 39.8))",
    },
    {
        "name": "Гранд-Каньон, США",
        "description": "Один из самых глубоких каньонов в мире",
        "difficulty": 4,
        "category": "nature",
        "country": "США",
        "region": "Аризона",
        "tags": ["каньон", "Колорадо"],
        "polygon": "POLYGON((-113.0 35.9, -113.0 36.3, -112.0 36.3, -112.0 35.9, -113.0 35.9))",
    },
    {
        "name": "Амазонка, Бразилия",
        "description": "Бассейн реки Амазонки с тропическими лесами",
        "difficulty": 5,
        "category": "nature",
        "country": "Бразилия",
        "region": "Амазонас",
        "tags": ["джунгли", "река"],
        "polygon": "POLYGON((-70.0 -5.0, -70.0 0.0, -60.0 0.0, -60.0 -5.0, -70.0 -5.0))",
    },
    {
        "name": "Сахара, Африка",
        "description": "Крупнейшая пустыня в мире",
        "difficulty": 5,
        "category": "desert",
        "country": "Алжир",
        "region": "Сахара",
        "tags": ["дюны", "пустыня"],
        "polygon": "POLYGON((-10.0 20.0, -10.0 30.0, 30.0 30.0, 30.0 20.0, -10.0 20.0))",
    },
    {
        "name": "Альпы, Европа",
        "description": "Крупнейший горный массив Европы",
        "difficulty": 4,
        "category": "mountains",
        "country": "Швейцария",
        "region": "Альпы",
        "tags": ["горы", "ледники"],
        "polygon": "POLYGON((5.0 44.0, 5.0 48.0, 15.0 48.0, 15.0 44.0, 5.0 44.0))",
    },
    {
        "name": "Гималаи, Азия",
        "description": "Высочайшая горная система Земли",
        "difficulty": 5,
        "category": "mountains",
        "country": "Непал",
        "region": "Гималаи",
        "tags": ["горы", "снег"],
        "polygon": "POLYGON((80.0 27.0, 80.0 30.0, 90.0 30.0, 90.0 27.0, 80.0 27.0))",
    },
    {
        "name": "Гавайи, США",
        "description": "Вулканический архипелаг в Тихом океане",
        "difficulty": 3,
        "category": "islands",
        "country": "США",
        "region": "Гавайи",
        "tags": ["острова", "вулканы"],
        "polygon": "POLYGON((-160.0 18.0, -160.0 22.0, -154.0 22.0, -154.0 18.0, -160.0 18.0))",
    },
    {
        "name": "Мальдивы",
        "description": "Коралловый архипелаг в Индийском океане",
        "difficulty": 4,
        "category": "islands",
        "country": "Мальдивы",
        "region": "Индийский океан",
        "tags": ["атоллы", "лагуны"],
        "polygon": "POLYGON((72.0 -1.0, 72.0 7.0, 74.0 7.0, 74.0 -1.0, 72.0 -1.0))",
    },
    {
        "name": "Антарктида (побережье)",
        "description": "Побережье самого южного континента",
        "difficulty": 5,
        "category": "polar",
        "country": "Антарктида",
        "region": "Земля Виктории",
        "tags": ["лёд", "шельф"],
        "polygon": "POLYGON((-70.0 -70.0, -70.0 -65.0, -60.0 -65.0, -60.0 -70.0, -70.0 -70.0))",
    },
    {
        "name": "Долина Царей, Египет",
        "description": "Древнеегипетский некрополь близ Луксора",
        "difficulty": 3,
        "category": "historical",
        "country": "Египет",
        "region": "Луксор",
        "tags": ["археология", "Нил"],
        "polygon": "POLYGON((32.5 25.6, 32.5 25.8, 32.7 25.8, 32.7 25.6, 32.5 25.6))",
    },
    {
        "name": "Мачу-Пикчу, Перу",
        "description": "Древний город инков в Андах",
        "difficulty": 4,
        "category": "historical",
        "country": "Перу",
        "region": "Куско",
        "tags": ["археология", "Анды"],
        "polygon": "POLYGON((-72.6 -13.2, -72.6 -13.1, -72.5 -13.1, -72.5 -13.2, -72.6 -13.2))",
    },
]


async def seed(only_new: bool = False) -> tuple[int, int]:
    """Загрузить зоны. Возвращает количество добавленных и обновлённых."""
    added = updated = 0

    async with AsyncSessionLocal() as session:
        existing = {
            zone.name: zone
            for zone in (await session.execute(select(LocationZone))).scalars().all()
        }

        for data in ZONES:
            zone = existing.get(data["name"])

            if zone is None:
                session.add(_build_zone(data))
                added += 1
                continue

            if only_new:
                continue

            _apply(zone, data)
            updated += 1

        await session.commit()

    return added, updated


def _build_zone(data: dict) -> LocationZone:
    zone = LocationZone(name=data["name"], is_active=True)
    _apply(zone, data)
    return zone


def _apply(zone: LocationZone, data: dict) -> None:
    zone.description = data["description"]
    zone.difficulty = data["difficulty"]
    zone.category = data["category"]
    zone.country = data["country"]
    zone.region = data["region"]
    zone.tags = json.dumps(data["tags"], ensure_ascii=False)
    zone.polygon = WKTElement(data["polygon"], srid=4326)


def main() -> None:
    parser = argparse.ArgumentParser(description="Загрузка игровых зон Location King")
    parser.add_argument(
        "--only-new",
        action="store_true",
        help="не трогать зоны, которые уже есть в базе",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")

    added, updated = asyncio.run(seed(only_new=args.only_new))
    logger.info(
        "Зоны загружены: добавлено %s, обновлено %s, всего в списке %s", added, updated, len(ZONES)
    )


if __name__ == "__main__":
    main()
