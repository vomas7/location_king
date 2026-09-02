"""
HTTP-слой знакомства с игрой без учётной записи.

Единственная часть API, открытая без токена. Считать здесь нечего по игроку —
его ещё нет, — поэтому все три эндпоинта ограничены по адресу клиента.
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import limit_by_address, request_language
from app.schemas.demo import DemoRoundsResponse
from app.schemas.game import GuessRequest, RoundResult
from app.services import demo as demo_service
from app.services import tiles as tiles_service
from app.services.rate_limit import Limit

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.get(
    "/rounds",
    response_model=DemoRoundsResponse,
    dependencies=[Depends(limit_by_address(Limit.DEMO))],
)
async def demo_rounds(
    language: str = Depends(request_language),
    db: AsyncSession = Depends(get_db),
) -> DemoRoundsResponse:
    """Пять раундов знакомства. Ни координат, ни правильных ответов в них нет."""
    prepared = await demo_service.rounds(db)
    await demo_service.started()

    return DemoRoundsResponse(
        rounds=[demo_service.round_view(demo_round, language) for demo_round in prepared]
    )


@router.post(
    "/rounds/{index}/guess",
    response_model=RoundResult,
    dependencies=[Depends(limit_by_address(Limit.DEMO))],
)
async def demo_guess(
    index: int,
    payload: GuessRequest,
    language: str = Depends(request_language),
    db: AsyncSession = Depends(get_db),
) -> RoundResult:
    """
    Принять ответ гостя и показать, где была цель.

    Правильный ответ до этого момента остаётся на сервере — то же правило,
    что и в настоящем раунде. Результат никуда не записывается: у гостя нет
    ни партии, ни истории, и таблицу лидеров знакомство не трогает.
    """
    demo_round = await demo_service.get_round(db, index)

    return await demo_service.answer(
        db, demo_round, point=payload.point, country=payload.country, language=language
    )


@router.get(
    "/rounds/{index}/tiles/{z}/{x}/{y}.jpg",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}}},
    dependencies=[Depends(limit_by_address(Limit.DEMO_TILES))],
)
async def demo_tile(
    index: int,
    z: int,
    x: int,
    y: int,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Тайл снимка знакомства по локальным координатам раунда.

    Глобальные координаты остаются на сервере, как и в игре: локальная сетка
    ничего не говорит о том, где это место на планете.

    Кэш публичный, а не приватный: пять мест знакомства одни и те же у всех,
    и раздавать их каждому заново незачем.
    """
    demo_round = await demo_service.get_round(db, index)
    tile = await tiles_service.get_tile(demo_round, z, x, y)

    return Response(
        content=tile,
        media_type=tiles_service.TILE_CONTENT_TYPE,
        headers={"Cache-Control": f"public, max-age={settings.tile_cache_ttl_seconds}"},
    )
