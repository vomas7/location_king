"""Зависимости FastAPI: сессия БД и текущий пользователь."""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AuthError
from app.models.user import User
from app.services import auth as auth_service

# auto_error=False — ошибку формируем сами, чтобы формат совпадал с остальным API
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Единственная точка авторизации в проекте."""
    if not token:
        raise AuthError("Требуется авторизация")

    user_id = auth_service.decode_token(token, "access")
    return await auth_service.get_active_user(db, user_id)


async def get_optional_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """
    Текущий пользователь, если токен есть и он валиден.

    Для страниц, которые открыты всем, но показывают больше авторизованному —
    например, таблица лидеров с местом самого игрока.
    """
    if not token:
        return None

    try:
        user_id = auth_service.decode_token(token, "access")
        return await auth_service.get_active_user(db, user_id)
    except AuthError:
        return None
