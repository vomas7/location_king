#!/usr/bin/env python3
"""
Загрузка границ стран.

Границы нужны режиму «угадай страну»: игрок ставит точку, а сервер решает, в
какую страну она попала. Решает именно сервер — отдать границы клиенту значит
отдать два мегабайта и вместе с ними подсказку.

Данные из OpenStreetMap через simonepri/geo-maps, лицензия ODbL. Версия
источника закреплена: «latest» однажды поменял бы границы под нами молча.

Разрешение в пять километров выбрано не на глаз: на нём проверено, что для
каждой зоны каталога страна по границам совпадает с той, что записана руками.
Точнее — только тяжелее, километровая сетка весит двадцать два мегабайта.

    python scripts/load_countries.py
    python scripts/load_countries.py --file /путь/к/countries.geo.json
"""

import argparse
import asyncio
import json
import logging
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.country import Country
from scripts.country_names import COUNTRY_NAMES

logger = logging.getLogger("countries")

SOURCE_VERSION = "v0.6.0"
SOURCE_URL = (
    "https://github.com/simonepri/geo-maps/releases/download/"
    f"{SOURCE_VERSION}/countries-land-5km.geo.json"
)

DOWNLOAD_TIMEOUT_SECONDS = 120


def read_source(path: Path | None) -> dict:
    """Прочитать границы из файла или скачать их."""
    if path is not None:
        logger.info("Читаю границы из %s", path)
        return json.loads(path.read_text(encoding="utf-8"))

    logger.info("Скачиваю границы: %s", SOURCE_URL)
    with urllib.request.urlopen(SOURCE_URL, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


async def load(session: AsyncSession, source: dict) -> int:
    """
    Заменить границы целиком.

    Не по одной стране: границы меняются набором, и половина старого набора
    вперемешку с половиной нового — это карта, которой не существует.
    """
    await session.execute(delete(Country))

    for feature in source["features"]:
        code = feature["properties"]["A3"]
        name = COUNTRY_NAMES.get(code)

        if name is None:
            raise ValueError(f"Нет русского названия для страны {code}")

        session.add(
            Country(
                code=code,
                name=name,
                # Разбирает PostGIS: он же потом с этой геометрией и работает.
                # ST_Multi приводит одиночные полигоны к общему типу столбца
                border=func.ST_Multi(
                    func.ST_SetSRID(func.ST_GeomFromGeoJSON(json.dumps(feature["geometry"])), 4326)
                ),
            )
        )

    await session.commit()
    return len(source["features"])


async def load_database(path: Path | None) -> int:
    async with AsyncSessionLocal() as session:
        return await load(session, read_source(path))


async def count() -> int:
    async with AsyncSessionLocal() as session:
        return (await session.execute(select(func.count(Country.code)))).scalar_one()


def main() -> None:
    parser = argparse.ArgumentParser(description="Загрузка границ стран Location King")
    parser.add_argument("--file", type=Path, help="локальный файл вместо скачивания")
    parser.add_argument(
        "--only-new",
        action="store_true",
        help="ничего не делать, если границы уже загружены",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")

    if args.only_new and asyncio.run(count()) > 0:
        logger.info("Границы уже загружены, пропускаю")
        return

    loaded = asyncio.run(load_database(args.file))
    logger.info("Границы загружены: %s стран", loaded)


if __name__ == "__main__":
    main()
