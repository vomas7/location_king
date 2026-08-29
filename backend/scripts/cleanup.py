#!/usr/bin/env python3
"""
Уборка брошенных партий и недосчитанных дуэлей.

Игрок может закрыть вкладку посреди игры: партия останется активной навсегда,
попадёт в «продолжить» через месяц и будет мешать статистике. Скрипт помечает
такие партии брошенными и пересчитывает статистику затронутых игроков.

Дуэли обычно досчитывает тот, кто дошёл до конца последним. Но если ушли оба
или победитель закрыл вкладку, не дождавшись соперника, звать некого — такие
дуэли добираются здесь.

Запускать по расписанию, например раз в час:

    python scripts/cleanup.py --older-than 6
"""

import argparse
import asyncio
import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.database import AsyncSessionLocal, engine
from app.models.enums import SessionStatus
from app.models.game_session import GameSession
from app.services import duels
from app.services.game import finish_session

logger = logging.getLogger("cleanup")

DEFAULT_HOURS = 6


async def abandon_stale_sessions(older_than_hours: int) -> int:
    """Пометить брошенными партии, в которых давно не было раундов."""
    threshold = datetime.now(UTC) - timedelta(hours=older_than_hours)

    async with AsyncSessionLocal() as session:
        stale = (
            (
                await session.execute(
                    select(GameSession).where(
                        GameSession.status == SessionStatus.ACTIVE,
                        GameSession.started_at < threshold,
                    )
                )
            )
            .scalars()
            .all()
        )

        for game_session in stale:
            await finish_session(session, game_session)

        await session.commit()

    return len(stale)


async def settle_abandoned_duels() -> int:
    """Начислить рейтинг по дуэлям, за которыми никто не вернулся."""
    async with AsyncSessionLocal() as session:
        settled = await duels.settle_stale(session)
        await session.commit()

    return settled


async def run(older_than: int) -> tuple[int, int]:
    """
    Вся уборка в одном цикле событий.

    Два `asyncio.run` подряд — это два цикла на один пул соединений: во
    второй цикл пул отдаёт соединение, открытое в первом, `pool_pre_ping`
    проверяет его — и asyncpg падает с «attached to a different loop».
    """
    try:
        return await abandon_stale_sessions(older_than), await settle_abandoned_duels()
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Уборка брошенных партий Location King")
    parser.add_argument(
        "--older-than",
        type=int,
        default=DEFAULT_HOURS,
        metavar="ЧАСОВ",
        help=f"через сколько часов партия считается брошенной (по умолчанию {DEFAULT_HOURS})",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")

    closed, settled = asyncio.run(run(args.older_than))

    logger.info("Брошенных партий закрыто: %s", closed)
    logger.info("Дуэлей досчитано: %s", settled)


if __name__ == "__main__":
    main()
