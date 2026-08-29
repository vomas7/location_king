"""HTTP-слой стран."""

import hashlib

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services import countries as countries_service

router = APIRouter(prefix="/api/countries", tags=["countries"])

#: Контуры меняются вместе с релизом, поэтому кэшируются надолго. Сверх того
#: ответ помечен ETag: при совпадении браузер не качает полмегабайта заново
CACHE_CONTROL = "public, max-age=86400"


@router.get("/borders")
async def country_borders(
    response: Response,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Контуры стран для карты догадки в режиме стран.

    Ответ никак не приближает к разгадке: на карте лежат границы всех стран
    сразу, и какая из них правильная, по ним не узнать. Проверяет ответ всё
    равно сервер, и по коду страны, а не по геометрии.
    """
    collection = await countries_service.outlines(db)
    tag = f'"{hashlib.sha256(collection.encode("utf-8")).hexdigest()[:16]}"'

    return Response(
        content=collection,
        media_type="application/json",
        headers={"Cache-Control": CACHE_CONTROL, "ETag": tag},
    )
