"""
Друзья.

Добавляют по короткому коду игрока. Не по имени: имена не уникальны, и поиск
по чужому имени — способ найти не того человека, а заодно способ собирать
чужие имена. Код игрок показывает сам, кому захочет.

Встречная заявка не создаёт вторую строку, а подтверждает первую: двое,
позвавшие друг друга, уже договорились, спрашивать их ещё раз незачем.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import messages
from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.enums import FriendshipStatus
from app.models.friendship import Friendship
from app.models.user import User
from app.observability import metrics

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Connection:
    """Связь глазами одного из двоих."""

    friendship: Friendship
    #: Второй участник — тот, кто не является смотрящим
    other: User
    #: Заявка пришла к смотрящему и ждёт его ответа
    incoming: bool


async def by_code(db: AsyncSession, code: str) -> User:
    """Игрок по коду. Регистр не важен."""
    stmt = select(User).where(
        User.friend_code == code.strip().upper(),
        User.is_active.is_(True),
    )
    user = (await db.execute(stmt)).scalar_one_or_none()

    if user is None:
        raise NotFoundError(messages.FRIEND_CODE_UNKNOWN)
    return user


async def between(db: AsyncSession, one: User, other: User) -> Friendship | None:
    """Связь этих двоих, в какую бы сторону она ни была заведена."""
    stmt = select(Friendship).where(
        or_(
            (Friendship.requester_id == one.id) & (Friendship.addressee_id == other.id),
            (Friendship.requester_id == other.id) & (Friendship.addressee_id == one.id),
        )
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def invite(db: AsyncSession, user: User, code: str) -> Connection:
    """Позвать в друзья по коду."""
    target = await by_code(db, code)

    if target.id == user.id:
        raise ValidationError(messages.FRIEND_CODE_OWN)

    existing = await between(db, user, target)

    if existing is not None:
        if existing.status == FriendshipStatus.ACCEPTED:
            raise ConflictError(messages.FRIEND_ALREADY)

        # Позвали в ответ: договорились оба, спрашивать больше не о чем
        if existing.addressee_id == user.id:
            return await accept(db, user, existing.id)

        raise ConflictError(messages.FRIEND_REQUEST_SENT)

    friendship = Friendship(
        requester_id=user.id,
        addressee_id=target.id,
        status=FriendshipStatus.PENDING,
    )
    db.add(friendship)
    await db.flush()

    await metrics.count("friend_invited")
    logger.info("Игрок %s позвал в друзья %s", user.id, target.id)

    return Connection(friendship=friendship, other=target, incoming=False)


async def accept(db: AsyncSession, user: User, friendship_id: int) -> Connection:
    """Принять заявку. Принять можно только адресованную себе."""
    friendship = await _own(db, user, friendship_id)

    if friendship.addressee_id != user.id:
        raise ConflictError(messages.FRIEND_REQUEST_YOURS)

    if friendship.status != FriendshipStatus.ACCEPTED:
        friendship.status = FriendshipStatus.ACCEPTED
        friendship.accepted_at = datetime.now(UTC)
        await db.flush()

        await metrics.count("friend_accepted")
        logger.info(
            "Игроки %s и %s теперь друзья",
            friendship.requester_id,
            friendship.addressee_id,
        )

    return Connection(friendship=friendship, other=friendship.requester, incoming=False)


async def remove(db: AsyncSession, user: User, friendship_id: int) -> None:
    """
    Убрать связь: отклонить заявку, отозвать свою или расстаться.

    Всё это одно и то же действие — строки больше нет, — и разделять его на
    три эндпоинта незачем.
    """
    friendship = await _own(db, user, friendship_id)

    await db.delete(friendship)
    await db.flush()

    logger.info("Связь %s убрана игроком %s", friendship_id, user.id)


async def connections(db: AsyncSession, user: User) -> list[Connection]:
    """Все связи игрока: и дружбы, и заявки в обе стороны."""
    stmt = (
        select(Friendship)
        .where(or_(Friendship.requester_id == user.id, Friendship.addressee_id == user.id))
        .options(selectinload(Friendship.requester), selectinload(Friendship.addressee))
        .order_by(Friendship.created_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()

    return [
        Connection(
            friendship=row,
            other=row.addressee if row.requester_id == user.id else row.requester,
            incoming=row.addressee_id == user.id and row.status == FriendshipStatus.PENDING,
        )
        for row in rows
    ]


async def circle(db: AsyncSession, user: User) -> tuple[int, ...]:
    """
    Круг игрока: подтверждённые друзья и он сам.

    Нужен таблице лидеров: зачёт среди друзей — это тот же зачёт, но по
    короткому списку. Себя в этот список включаем здесь, а не в таблице:
    «среди друзей» без самого игрока — это чужая таблица, а не своя.
    """
    stmt = select(Friendship).where(
        Friendship.status == FriendshipStatus.ACCEPTED,
        or_(Friendship.requester_id == user.id, Friendship.addressee_id == user.id),
    )
    rows = (await db.execute(stmt)).scalars().all()

    return (
        *(row.addressee_id if row.requester_id == user.id else row.requester_id for row in rows),
        user.id,
    )


async def _own(db: AsyncSession, user: User, friendship_id: int) -> Friendship:
    """Связь, в которой участвует игрок. Чужая — как несуществующая."""
    stmt = (
        select(Friendship)
        .where(
            Friendship.id == friendship_id,
            or_(Friendship.requester_id == user.id, Friendship.addressee_id == user.id),
        )
        .options(selectinload(Friendship.requester), selectinload(Friendship.addressee))
    )
    friendship = (await db.execute(stmt)).scalar_one_or_none()

    if friendship is None:
        raise NotFoundError(messages.FRIEND_REQUEST_UNKNOWN)
    return friendship
