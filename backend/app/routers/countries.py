"""HTTP-слой стран."""

import hashlib

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import limit_by_address, request_language
from app.services import countries as countries_service
from app.services.rate_limit import Limit

router = APIRouter(prefix="/api/countries", tags=["countries"])

#: Контуры меняются вместе с релизом, поэтому кэшируются надолго. Сверх того
#: ответ помечен ETag: при совпадении браузер не качает полмегабайта заново
CACHE_CONTROL = "public, max-age=86400"


@router.get("/borders", dependencies=[Depends(limit_by_address(Limit.BORDERS))])
async def country_borders(
    response: Response,
    language: str = Depends(request_language),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Контуры стран для карты догадки в режиме стран.

    Открыты и без токена: те же границы нужны гостю в знакомстве с игрой, а
    к разгадке ответ не приближает никого — на карте лежат границы всех стран
    сразу, и какая из них правильная, по ним не узнать. Проверяет ответ всё
    равно сервер, и по коду страны, а не по геометрии.

    Считается по адресу клиента: игрока за этим запросом может и не быть.
    """
    collection = await countries_service.outlines(db, language)
    tag = f'"{hashlib.sha256(collection.encode("utf-8")).hexdigest()[:16]}"'

    return Response(
        content=collection,
        media_type="application/json",
        headers={"Cache-Control": CACHE_CONTROL, "ETag": tag},
    )
