"""Зависимости FastAPI: сессия БД, текущий пользователь, ограничение частоты."""

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AuthError
from app.models.user import User
from app.services import auth as auth_service
from app.services import rate_limit
from app.services.rate_limit import Limit

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


def client_address(request: Request) -> str:
    """
    Адрес клиента.

    Приложение всегда стоит за nginx из этого репозитория, и он проставляет
    X-Forwarded-For сам: в контуре cloudflare — проверенный адрес игрока из
    CF-Connecting-IP, в остальных — цепочку от предыдущего прокси. То, что
    прислал клиент, в первом случае не пересылается вовсе.

    Если выставить бэкенд наружу напрямую, заголовок можно будет подделать —
    тогда его нужно перестать читать.
    """
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()

    return request.client.host if request.client else "unknown"


def limit_by_address(limit: Limit) -> Callable[..., Coroutine[Any, Any, None]]:
    """Ограничение частоты по адресу клиента — для запросов без авторизации."""

    async def dependency(request: Request) -> None:
        await rate_limit.check(limit, client_address(request))

    return dependency


def limit_by_user(limit: Limit) -> Callable[..., Coroutine[Any, Any, None]]:
    """Ограничение частоты по игроку — для запросов с токеном."""

    async def dependency(user: User = Depends(get_current_user)) -> None:
        await rate_limit.check(limit, str(user.id))

    return dependency
