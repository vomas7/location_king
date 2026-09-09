#!/usr/bin/env python3
"""
Заведение соперников-ботов.

Бот — обычная учётная запись с поднятым флагом, поэтому и появляется он в базе
как запись, а не как строка в коде. Скрипт повторяем: заводится только тот,
кого ещё нет, уровни и имена берутся из `app/services/bots.py`.

    python scripts/seed_bots.py
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import AsyncSessionLocal, engine
from app.services import bots as bots_service

logger = logging.getLogger("bots")


async def run() -> int:
    """Завести недостающих ботов и вернуть, сколько их стало всего."""
    try:
        async with AsyncSessionLocal() as session:
            bots = await bots_service.ensure(session)
            await session.commit()

            return len(bots)
    finally:
        await engine.dispose()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")

    logger.info("Соперников-ботов в игре: %s", asyncio.run(run()))


if __name__ == "__main__":
    main()
