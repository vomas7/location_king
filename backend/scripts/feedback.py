#!/usr/bin/env python3
"""
Что игроки написали об игре.

Форма в меню кладёт отзывы в базу, а читают их отсюда. Отдельного экрана
администратора в игре нет намеренно: пока отзыв — это строка с текстом и
именем, экран ради неё стоил бы дороже, чем даёт.

    python scripts/feedback.py
    python scripts/feedback.py --kind problem --limit 50
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import AsyncSessionLocal, engine
from app.models.enums import FeedbackKind
from app.services import feedback as feedback_service

logger = logging.getLogger("feedback")

DEFAULT_LIMIT = 20

KIND_LABELS = {
    FeedbackKind.IMPRESSION: "впечатление",
    FeedbackKind.PROBLEM: "проблема",
}


async def show(limit: int, kind: FeedbackKind | None) -> int:
    """Напечатать свежие отзывы. Возвращает, сколько их нашлось."""
    try:
        async with AsyncSessionLocal() as session:
            entries = await feedback_service.recent(session, limit, kind)

        for entry in entries:
            when = entry.created_at.strftime("%d.%m.%Y %H:%M")
            who = entry.author.display_name or entry.author.username
            print(f"\n── {when}  {KIND_LABELS[FeedbackKind(entry.kind)]}  ·  {who}")
            print(entry.message)

        return len(entries)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Отзывы игроков Location King")
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"сколько последних показать (по умолчанию {DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--kind",
        choices=[kind.value for kind in FeedbackKind],
        help="показать только впечатления или только проблемы",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")

    found = asyncio.run(show(args.limit, FeedbackKind(args.kind) if args.kind else None))

    if found == 0:
        logger.info("Отзывов пока нет")
        return

    logger.info("Показано отзывов: %s", found)


if __name__ == "__main__":
    main()
