#!/usr/bin/env python3
"""
Что игроки на самом деле делают в игре.

Отдельного экрана администратора в игре нет: пока вопросов к статистике
десяток, скрипт стоит дешевле экрана. Считает только по своей базе и ничего
не меняет — запускать безопасно в любой момент.

    docker compose exec -T backend python scripts/stats.py

Разделы выбираются по имени, если нужен один:

    docker compose exec -T backend python scripts/stats.py --only scoring
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import AsyncSessionLocal, engine

logger = logging.getLogger("stats")

#: Ширина колонки с подписью. Отчёт читают глазами в терминале, а не парсят
LABEL_WIDTH = 34

QUERIES: dict[str, tuple[str, str]] = {
    "users": (
        "Игроки",
        """
        SELECT
            count(*)                                            AS "всего",
            count(*) FILTER (WHERE games_played = 0)            AS "ни одной партии",
            count(*) FILTER (WHERE games_played BETWEEN 1 AND 2) AS "1-2 партии",
            count(*) FILTER (WHERE games_played BETWEEN 3 AND 9) AS "3-9 партий",
            count(*) FILTER (WHERE games_played >= 10)          AS "10 и больше",
            count(*) FILTER (WHERE created_at > now() - interval '7 days') AS "за неделю"
        FROM users
        """,
    ),
    "sessions": (
        "Партии",
        """
        SELECT
            count(*)                                          AS "всего",
            count(*) FILTER (WHERE status = 'finished')       AS "доиграны",
            count(*) FILTER (WHERE status = 'active')         AS "брошены на середине",
            round(avg(rounds_done)::numeric, 2)               AS "раундов в среднем",
            round(avg(rounds_total)::numeric, 2)              AS "заказано раундов",
            count(*) FILTER (WHERE challenge_day IS NOT NULL) AS "челлендж дня",
            count(*) FILTER (WHERE match_code IS NOT NULL)    AS "в комнате"
        FROM game_sessions
        """,
    ),
    "quit": (
        "На каком раунде бросают",
        """
        SELECT rounds_done AS "раундов сыграно", count(*) AS "партий"
        FROM game_sessions
        WHERE status = 'active' AND started_at < now() - interval '1 day'
        GROUP BY 1 ORDER BY 1
        """,
    ),
    "scoring": (
        "Промах и очки в раундах по точке",
        """
        SELECT
            count(*)                                              AS "раундов",
            round(percentile_cont(0.10) WITHIN GROUP (ORDER BY distance_km)::numeric, 1) AS "промах p10",
            round(percentile_cont(0.25) WITHIN GROUP (ORDER BY distance_km)::numeric, 1) AS "p25",
            round(percentile_cont(0.50) WITHIN GROUP (ORDER BY distance_km)::numeric, 1) AS "медиана",
            round(percentile_cont(0.75) WITHIN GROUP (ORDER BY distance_km)::numeric, 1) AS "p75",
            round(percentile_cont(0.90) WITHIN GROUP (ORDER BY distance_km)::numeric, 1) AS "p90",
            round(avg(score)::numeric, 0)                         AS "очков в среднем",
            count(*) FILTER (WHERE score = 0)                     AS "нулевых",
            round(100.0 * count(*) FILTER (WHERE score = 0) / nullif(count(*), 0), 1) AS "доля нулевых, %"
        FROM rounds
        WHERE status <> 'active' AND distance_km IS NOT NULL AND country_code IS NULL
        """,
    ),
    "bands": (
        "Сколько очков дают за такой промах сейчас",
        """
        SELECT
            CASE
                WHEN distance_km <   5 THEN 'до 5 км'
                WHEN distance_km <  25 THEN '5-25 км'
                WHEN distance_km < 100 THEN '25-100 км'
                WHEN distance_km < 500 THEN '100-500 км'
                WHEN distance_km < 2000 THEN '500-2000 км'
                ELSE 'дальше 2000 км'
            END                              AS "промах",
            count(*)                         AS "раундов",
            round(avg(score)::numeric, 0)    AS "очков в среднем",
            count(*) FILTER (WHERE score = 0) AS "из них нулевых"
        FROM rounds
        WHERE status <> 'active' AND distance_km IS NOT NULL AND country_code IS NULL
        GROUP BY 1
        ORDER BY min(distance_km)
        """,
    ),
    "extent": (
        "Насколько широкий кадр заказывают",
        """
        SELECT
            CASE
                WHEN view_extent_km <  20 THEN 'до 20 км'
                WHEN view_extent_km <  45 THEN '20-45 км'
                WHEN view_extent_km <  90 THEN '45-90 км'
                WHEN view_extent_km < 180 THEN '90-180 км'
                ELSE 'шире 180 км'
            END                              AS "кадр",
            count(*)                         AS "раундов",
            round(avg(distance_km)::numeric, 0) AS "промах в среднем",
            round(avg(score)::numeric, 0)    AS "очков в среднем",
            round(100.0 * count(*) FILTER (WHERE score = 0) / nullif(count(*), 0), 1) AS "нулевых, %"
        FROM rounds
        WHERE status <> 'active' AND country_code IS NULL
        GROUP BY 1 ORDER BY min(view_extent_km)
        """,
    ),
    "setup": (
        "Какие условия выбирают",
        """
        SELECT
            coalesce(difficulty, 'любой')     AS "уровень",
            coalesce(continent, 'весь мир')   AS "часть света",
            coalesce(country_group, '—')      AS "подборка",
            answer_mode                       AS "чем отвечать",
            count(*)                          AS "серий"
        FROM round_series
        GROUP BY 1, 2, 3, 4
        ORDER BY 5 DESC
        LIMIT 25
        """,
    ),
    "timer": (
        "Играют ли на время",
        """
        SELECT
            coalesce(time_limit_seconds::text, 'без таймера') AS "лимит",
            count(*)                                          AS "партий",
            count(*) FILTER (WHERE status = 'finished')       AS "доиграны"
        FROM game_sessions
        GROUP BY 1 ORDER BY 2 DESC
        """,
    ),
    "repeats": (
        "Повторы зон внутри одной партии",
        """
        WITH per_session AS (
            SELECT session_id, count(*) AS rounds, count(DISTINCT zone_id) AS zones
            FROM rounds GROUP BY session_id
        )
        SELECT
            count(*)                                    AS "партий",
            count(*) FILTER (WHERE zones < rounds)      AS "с повтором зоны",
            round(100.0 * count(*) FILTER (WHERE zones < rounds) / nullif(count(*), 0), 1)
                                                        AS "доля, %",
            max(rounds - zones)                         AS "худший случай, лишних раундов"
        FROM per_session
        WHERE rounds > 1
        """,
    ),
    "zones": (
        "Самые частые зоны",
        """
        SELECT z.name AS "зона", z.country AS "страна", count(*) AS "раундов"
        FROM rounds r JOIN location_zones z ON z.id = r.zone_id
        GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 15
        """,
    ),
    "modes": (
        "Режимы ответа в сыгранных раундах",
        """
        SELECT
            CASE
                WHEN country_code IS NULL THEN 'точкой'
                WHEN choices IS NOT NULL  THEN 'из шести'
                ELSE 'страной'
            END                              AS "режим",
            count(*)                         AS "раундов",
            round(avg(score)::numeric, 0)    AS "очков в среднем",
            round(100.0 * count(*) FILTER (WHERE score = 0) / nullif(count(*), 0), 1) AS "нулевых, %"
        FROM rounds
        WHERE status <> 'active'
        GROUP BY 1 ORDER BY 2 DESC
        """,
    ),
    "hints": (
        "Подсказки",
        """
        SELECT
            count(*) FILTER (WHERE hint_used)  AS "раундов с подсказкой",
            count(*)                           AS "раундов всего",
            round(100.0 * count(*) FILTER (WHERE hint_used) / nullif(count(*), 0), 1) AS "доля, %"
        FROM rounds WHERE status <> 'active'
        """,
    ),
    "timeouts": (
        "Чем кончаются раунды",
        """
        SELECT status AS "статус", count(*) AS "раундов"
        FROM rounds GROUP BY 1 ORDER BY 2 DESC
        """,
    ),
}


def render(title: str, columns: list[str], rows: list[tuple]) -> str:
    """Одна таблица отчёта. Узкие таблицы печатаются в строку, широкие — сеткой."""
    if not rows:
        return f"\n{title}\n  пусто"

    # Один ряд — это сводка, и читается она парами «подпись: значение»
    if len(rows) == 1:
        lines = [
            f"  {name:<{LABEL_WIDTH}} {'—' if value is None else value}"
            for name, value in zip(columns, rows[0], strict=True)
        ]
        return f"\n{title}\n" + "\n".join(lines)

    widths = [
        max(len(str(name)), *(len("—" if row[i] is None else str(row[i])) for row in rows))
        for i, name in enumerate(columns)
    ]
    header = "  " + "  ".join(str(name).ljust(widths[i]) for i, name in enumerate(columns))
    ruler = "  " + "  ".join("-" * width for width in widths)
    body = [
        "  "
        + "  ".join(
            ("—" if cell is None else str(cell)).ljust(widths[i]) for i, cell in enumerate(row)
        )
        for row in rows
    ]
    return "\n".join([f"\n{title}", header, ruler, *body])


async def report(only: str | None) -> None:
    """Напечатать отчёт целиком или один его раздел."""
    async with AsyncSessionLocal() as session:
        for key, (title, sql) in QUERIES.items():
            if only is not None and only != key:
                continue

            result = await session.execute(text(sql))
            print(render(title, list(result.keys()), [tuple(row) for row in result.all()]))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(description="Статистика игры")
    parser.add_argument("--only", choices=sorted(QUERIES), help="показать один раздел")
    args = parser.parse_args()

    async def run() -> None:
        try:
            await report(args.only)
        finally:
            await engine.dispose()

    asyncio.run(run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
