"""
Аутентификация: хеширование паролей и выпуск JWT.

Пароли хешируются argon2id. Токенов два: короткий access и длинный refresh,
различаются полем type — refresh-токен нельзя предъявить вместо access.
"""

import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error, InvalidHashError
from jose import JWTError, jwt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import AuthError, ConflictError
from app.models.user import User

logger = logging.getLogger(__name__)

TokenType = Literal["access", "refresh"]

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Хеш пароля argon2id."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """
    Проверить пароль.

    Несовпадение и испорченный хеш в базе — одно и то же для вызывающего:
    войти нельзя. Всё остальное пусть падает.
    """
    try:
        return _hasher.verify(password_hash, password)
    except (Argon2Error, InvalidHashError, UnicodeEncodeError):
        return False


def create_token(user_id: int, token_type: TokenType) -> str:
    """Выпустить подписанный JWT для пользователя."""
    now = datetime.now(UTC)
    ttl = (
        timedelta(minutes=settings.access_token_ttl_minutes)
        if token_type == "access"
        else timedelta(days=settings.refresh_token_ttl_days)
    )

    payload = {
        "sub": str(user_id),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: TokenType) -> int:
    """Проверить подпись и срок токена, вернуть id пользователя."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise AuthError("Токен недействителен или истёк") from e

    if payload.get("type") != expected_type:
        raise AuthError(f"Ожидался токен типа {expected_type}")

    subject = payload.get("sub")
    if subject is None:
        raise AuthError("Токен не содержит идентификатор пользователя")

    return int(subject)


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Найти пользователя по email без учёта регистра."""
    stmt = select(User).where(func.lower(User.email) == email.strip().lower())
    return (await db.execute(stmt)).scalar_one_or_none()


async def register(db: AsyncSession, email: str, password: str, display_name: str | None) -> User:
    """Создать пользователя с email и паролем."""
    email = email.strip().lower()

    if await get_user_by_email(db, email) is not None:
        raise ConflictError("Пользователь с таким email уже зарегистрирован")

    user = User(
        username=await _unique_username(db, email.split("@")[0]),
        email=email,
        password_hash=hash_password(password),
        display_name=display_name or email.split("@")[0],
        is_guest=False,
        last_login_at=datetime.now(UTC),
    )
    db.add(user)
    await db.flush()

    logger.info("Зарегистрирован пользователь %s", user.id)
    return user


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    """Проверить пару email/пароль и вернуть пользователя."""
    user = await get_user_by_email(db, email)

    # Пароль проверяем даже для несуществующего пользователя — иначе по времени
    # ответа можно узнать, какие email зарегистрированы.
    password_hash = user.password_hash if user and user.password_hash else _DUMMY_HASH
    password_ok = verify_password(password, password_hash)

    if user is None or not password_ok:
        raise AuthError("Неверный email или пароль")
    if not user.is_active:
        raise AuthError("Учётная запись отключена")

    user.last_login_at = datetime.now(UTC)
    return user


async def create_guest(db: AsyncSession) -> User:
    """Создать гостя — играть можно без регистрации."""
    suffix = secrets.token_hex(4)
    user = User(
        username=f"guest_{suffix}",
        display_name=f"Гость {suffix[:4].upper()}",
        is_guest=True,
        last_login_at=datetime.now(UTC),
    )
    db.add(user)
    await db.flush()

    logger.info("Создан гость %s", user.id)
    return user


async def get_active_user(db: AsyncSession, user_id: int) -> User:
    """Загрузить активного пользователя по id."""
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthError("Пользователь не найден или отключён")
    return user


async def _unique_username(db: AsyncSession, base: str) -> str:
    """Подобрать свободный username на основе локальной части email."""
    base = "".join(ch for ch in base.lower() if ch.isalnum() or ch in "-_")[:32] or "player"

    candidate = base
    while (await db.execute(select(User.id).where(User.username == candidate))).first():
        candidate = f"{base}_{secrets.token_hex(2)}"

    return candidate


# Хеш-пустышка для сравнения при неизвестном email
_DUMMY_HASH = hash_password(secrets.token_hex(16))
