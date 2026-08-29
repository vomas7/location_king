#!/usr/bin/env python3
"""
Проверка каталога на воду.

Точка раунда берётся случайно внутри зоны, а приморская зона наполовину
состоит из моря. Игра отсеивает точки, в кадре которых нет суши, но зона, где
таких точек почти не остаётся, всё равно плохая: перебор упирается в потолок,
а кадр раз за разом показывает один и тот же клочок берега. Такие места лучше
поправить в scripts/seed.py — сдвинуть центр или уменьшить радиус — или
убрать вовсе.

Считается то же самое, что проверяет игра: доля точек зоны, в кадре которых
есть суша. Сушей считаются границы стран из таблицы countries, их сначала
нужно загрузить (scripts/load_countries.py).

    python scripts/check_zones.py
    python scripts/check_zones.py --below 40 --view 5
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.database import AsyncSessionLocal, engine
from app.services.zones import KM_PER_DEGREE, LAND_IN_FRAME

logger = logging.getLogger("check-zones")

#: Сколько точек бросить в каждую зону. Сорок — та же цифра, с которой игра
#: ищет сушу для раунда, поэтому доля попаданий и есть её шанс с первого раза
PROBES = 40

#: Кадр, для которого считается проверка. Пятнадцать километров — середина
#: шкалы и то, что стоит по умолчанию; в узком кадре берег должен быть ближе
DEFAULT_VIEW_KM = 15.0

REPORT = text("""
    WITH probe AS (
        SELECT z.id, z.name, z.country, z.tier,
               (ST_Dump(ST_GeneratePoints(z.polygon, :probes))).geom AS point
        FROM location_zones z
        WHERE z.is_active
    )
    SELECT name, country, tier,
           round(100.0 * count(*) FILTER (
               WHERE EXISTS (
                   SELECT 1 FROM countries WHERE ST_DWithin(border, probe.point, :near)
               )
           ) / count(*)) AS land_pct
    FROM probe
    GROUP BY id, name, country, tier
    ORDER BY land_pct, name
""")


async def run(below: int, view_km: float) -> int:
    async with AsyncSessionLocal() as session:
        loaded = (await session.execute(text("SELECT count(*) FROM countries"))).scalar_one()
        if loaded == 0:
            logger.error("Границы стран не загружены: сначала scripts/load_countries.py")
            return 1

        near = view_km * LAND_IN_FRAME / KM_PER_DEGREE
        rows = (await session.execute(REPORT, {"probes": PROBES, "near": near})).all()

    bad = [row for row in rows if row.land_pct < below]

    logger.info(
        "Зон в каталоге: %s. При виде на %s км суша попадает в кадр реже чем в %s%% точек — у %s",
        len(rows),
        round(view_km),
        below,
        len(bad),
    )
    for row in bad:
        logger.info("  %3s%%  %-28s %-22s %s", row.land_pct, row.name, row.country, row.tier)

    return 1 if bad else 0


async def main() -> int:
    parser = argparse.ArgumentParser(description="В скольких кадрах зоны видно сушу")
    parser.add_argument(
        "--below",
        type=int,
        default=40,
        help="Показать зоны, где суша попадает в кадр реже этой доли (по умолчанию 40)",
    )
    parser.add_argument(
        "--view",
        type=float,
        default=DEFAULT_VIEW_KM,
        dest="view_km",
        help="Ширина кадра в километрах (по умолчанию 15)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    try:
        return await run(args.below, args.view_km)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
