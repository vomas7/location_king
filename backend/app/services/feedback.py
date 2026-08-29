"""
Обратная связь от игроков.

Слой тонкий намеренно: отзыв — это строка в базе, а не бизнес-процесс. Вся
ценность здесь в том, что его можно прочитать, поэтому рядом лежит и выборка
свежего — ею пользуется scripts/feedback.py.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.enums import FeedbackKind
from app.models.feedback import Feedback
from app.models.user import User
from app.observability import metrics

logger = logging.getLogger(__name__)


async def leave(db: AsyncSession, user: User, kind: FeedbackKind, message: str) -> Feedback:
    """Записать отзыв игрока."""
    entry = Feedback(user_id=user.id, kind=kind, message=message)

    db.add(entry)
    await db.flush()

    logger.info("Игрок %s оставил отзыв %s (%s символов)", user.id, kind, len(message))
    await metrics.count("feedback_left")

    return entry


async def recent(db: AsyncSession, limit: int, kind: FeedbackKind | None = None) -> list[Feedback]:
    """Свежие отзывы вместе с их авторами."""
    query = (
        select(Feedback)
        .options(joinedload(Feedback.author))
        .order_by(Feedback.created_at.desc())
        .limit(limit)
    )

    if kind is not None:
        query = query.where(Feedback.kind == kind)

    return list((await db.execute(query)).scalars().all())
