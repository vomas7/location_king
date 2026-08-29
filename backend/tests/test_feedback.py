"""
Обратная связь.

Форма нужна, чтобы игрок мог рассказать о впечатлении и о поломке. Проверки
про то, что написанное доезжает до базы, читается обратно и уходит вместе с
учётной записью, — последнее обещано политикой конфиденциальности.
"""

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import FeedbackKind
from app.models.feedback import Feedback
from app.models.user import User
from app.schemas.feedback import MAX_MESSAGE_LENGTH
from app.services import feedback as feedback_service


async def test_feedback_reaches_the_database(
    client: AsyncClient,
    auth_headers: dict,
    db: AsyncSession,
):
    response = await client.post(
        "/api/feedback",
        json={"kind": "impression", "message": "Хардкор — это боль, спасибо"},
        headers=auth_headers,
    )

    assert response.status_code == 201
    assert response.json()["kind"] == "impression"

    stored = (await db.execute(select(Feedback))).scalars().all()
    assert len(stored) == 1
    assert stored[0].message == "Хардкор — это боль, спасибо"


async def test_blank_message_is_rejected(client: AsyncClient, auth_headers: dict):
    """Пробелы — это промах по кнопке, а не сообщение."""
    response = await client.post(
        "/api/feedback",
        json={"kind": "problem", "message": "   \n  "},
        headers=auth_headers,
    )

    assert response.status_code == 422


async def test_message_is_trimmed(client: AsyncClient, auth_headers: dict, db: AsyncSession):
    await client.post(
        "/api/feedback",
        json={"kind": "problem", "message": "  карта не открывается  "},
        headers=auth_headers,
    )

    stored = (await db.execute(select(Feedback))).scalars().one()
    assert stored.message == "карта не открывается"


async def test_huge_message_is_rejected(client: AsyncClient, auth_headers: dict):
    """Ограничение защищает базу от того, кто вставит туда мегабайт."""
    response = await client.post(
        "/api/feedback",
        json={"kind": "problem", "message": "я" * (MAX_MESSAGE_LENGTH + 1)},
        headers=auth_headers,
    )

    assert response.status_code == 422


async def test_unknown_kind_is_rejected(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/feedback",
        json={"kind": "жалоба", "message": "что-то"},
        headers=auth_headers,
    )

    assert response.status_code == 422


async def test_feedback_needs_authorization(client: AsyncClient):
    response = await client.post(
        "/api/feedback",
        json={"kind": "impression", "message": "аноним"},
    )

    assert response.status_code == 401


async def test_recent_returns_newest_first_and_filters_by_kind(
    db: AsyncSession,
    registered_user: User,
):
    await feedback_service.leave(db, registered_user, FeedbackKind.IMPRESSION, "первое")
    await feedback_service.leave(db, registered_user, FeedbackKind.PROBLEM, "второе")
    await feedback_service.leave(db, registered_user, FeedbackKind.IMPRESSION, "третье")

    newest = await feedback_service.recent(db, limit=10)
    assert [entry.message for entry in newest] == ["третье", "второе", "первое"]

    problems = await feedback_service.recent(db, limit=10, kind=FeedbackKind.PROBLEM)
    assert [entry.message for entry in problems] == ["второе"]


async def test_feedback_leaves_with_the_account(
    client: AsyncClient,
    auth_headers: dict,
    registered_user: User,
    db: AsyncSession,
):
    """Политика обещает, что данные можно стереть. Отзыв — такие же данные."""
    await client.post(
        "/api/feedback",
        json={"kind": "problem", "message": "сотрите меня вместе с аккаунтом"},
        headers=auth_headers,
    )

    response = await client.post(
        "/api/auth/me/delete",
        json={"password": "correct horse battery"},
        headers=auth_headers,
    )
    assert response.status_code == 204

    left = (await db.execute(select(func.count(Feedback.id)))).scalar_one()
    assert left == 0
