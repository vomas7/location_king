"""
Заготовленные серии раундов.

Одна реализация на две задачи: челлендж дня и комната мультиплеера отличаются
только тем, кто и когда играет серию, а сама серия устроена одинаково.
"""

import logging
from decimal import Decimal

from geoalchemy2 import WKTElement
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.exceptions import ConflictError, NotFoundError
from app.models.enums import CATALOG_ALIASES, AnswerMode
from app.models.game_session import GameSession
from app.models.round import Round
from app.models.series import RoundSeries, SeriesRound
from app.services import countries as countries_service
from app.services import tiles
from app.services import zones as zones_service
from app.services.round_timer import deadline_for
from app.services.scoring import MAX_ROUND_SCORE
from app.utils.geo import lonlat_to_tile, tile_center, tile_width_km, zoom_for_extent

logger = logging.getLogger(__name__)

# Сколько раундов может быть в серии. Верхняя граница не техническая: серия
# собирается целиком в одном запросе, и двадцать раундов — уже долгая партия.
MIN_ROUNDS = 1
MAX_ROUNDS = 20

# Сколько зон перебрать, прежде чем признать, что подходящих мест под
# заданные условия нет. Перебирать приходится по двум поводам: зона может
# оказаться целиком в воде и не годиться ни для какого режима, а в режиме
# стран каталог с границами может разойтись в названии страны
ZONE_ATTEMPTS = 12


async def create(
    db: AsyncSession,
    rounds_total: int,
    view_extent_km: float,
    category: str | None = None,
    continent: str | None = None,
    country_group: str | None = None,
    difficulty: str | None = None,
    zone_id: int | None = None,
    answer_mode: str = AnswerMode.POINT,
) -> RoundSeries:
    """Собрать серию раундов и сохранить её."""
    if not MIN_ROUNDS <= rounds_total <= MAX_ROUNDS:
        raise ConflictError(f"Раундов в серии должно быть от {MIN_ROUNDS} до {MAX_ROUNDS}")

    # Зоны, которые в этой серии уже были: одна и та же территория дважды за
    # партию — самая частая жалоба игроков. Набор общий на всю серию и растёт
    # по мере её сборки
    used: set[int] = set()

    rounds = [
        await _build_round(
            db,
            position,
            view_extent_km,
            category,
            continent,
            country_group,
            difficulty,
            zone_id,
            answer_mode,
            used,
        )
        for position in range(1, rounds_total + 1)
    ]

    # Раунды кладутся сразу в связь: иначе обращение к series.rounds полезло бы
    # в базу за тем, что только что создали
    # Условия запоминаем вместе с серией: по ним делится таблица лидеров, а
    # больше их хранить негде — раунды уже собраны и о выборе игрока не знают
    series = RoundSeries(
        rounds=rounds,
        difficulty=difficulty,
        continent=continent,
        country_group=country_group,
        answer_mode=answer_mode,
    )
    db.add(series)
    await db.flush()

    logger.info("Серия %s собрана: %s раундов", series.id, rounds_total)
    return series


async def load(db: AsyncSession, series_id: int) -> RoundSeries:
    """Серия вместе с раундами."""
    stmt = (
        select(RoundSeries)
        .where(RoundSeries.id == series_id)
        .options(selectinload(RoundSeries.rounds))
    )
    series = (await db.execute(stmt)).scalar_one_or_none()

    if series is None:
        raise NotFoundError(f"Серия {series_id} не найдена")
    return series


async def open_round(db: AsyncSession, session: GameSession, position: int) -> Round:
    """Скопировать заготовку серии в раунд игрока."""
    if session.series_id is None:
        raise ConflictError("Партия не привязана к серии")

    series = await load(db, session.series_id)
    template = next((item for item in series.rounds if item.position == position), None)

    if template is None:
        raise ConflictError(f"В серии {series.id} нет раунда {position}")

    round_obj = Round(
        session_id=session.id,
        position=position,
        zone_id=template.zone_id,
        target_point=template.target_point,
        country_code=template.country_code,
        choices=template.choices,
        tile_zoom=template.tile_zoom,
        tile_x=template.tile_x,
        tile_y=template.tile_y,
        view_extent_km=template.view_extent_km,
        max_score=MAX_ROUND_SCORE,
        deadline_at=deadline_for(session),
    )
    db.add(round_obj)

    await db.flush()
    await db.refresh(round_obj, ["zone"])

    tiles.schedule_prewarm(round_obj)

    return round_obj


async def _build_round(
    db: AsyncSession,
    position: int,
    view_extent_km: float,
    category: str | None,
    continent: str | None,
    country_group: str | None,
    difficulty: str | None = None,
    zone_id: int | None = None,
    answer_mode: str = AnswerMode.POINT,
    used: set[int] | None = None,
) -> SeriesRound:
    """
    Заготовка одного раунда серии.

    Внутри зоны выбирается случайная точка, под неё подбирается тайл нужного
    масштаба, и целью раунда становится центр этого тайла — именно его игрок
    и видит в центре снимка.

    `used` — зоны, уже занятые другими раундами этой серии: собранная зона
    добавляется туда сама. Зона, которая не подошла — оказалась в воде или
    разошлась с границами, — тоже перестаёт предлагаться, но только внутри
    этого раунда: в следующем она может подойти под другую точку.
    """
    borders_loaded = await countries_service.are_loaded(db)
    taken = set() if used is None else used
    skip = set(taken)

    for _ in range(ZONE_ATTEMPTS):
        zone = (
            await zones_service.get_zone(db, zone_id)
            if zone_id is not None
            else await zones_service.pick_random_zone(
                db, category, continent, country_group, difficulty=difficulty, exclude=skip
            )
        )
        skip.add(zone.id)

        # Точка раунда обязана быть на суше: приморская зона наполовину
        # состоит из моря, и без этого игрок регулярно получал кадр ровной
        # синевы, по которому угадать нельзя ничего
        point = (
            await zones_service.random_point_with_land(db, zone, view_extent_km)
            if borders_loaded
            else await zones_service.random_point_in_zone(db, zone)
        )

        if point is None:
            logger.info("Зона %s целиком в воде: суши в ней не нашлось", zone.name)
            if zone_id is not None:
                raise NotFoundError(f"Зона {zone.name} целиком в воде")
            continue

        lon, lat = point

        zoom = zoom_for_extent(lat, view_extent_km, max_zoom=settings.satellite_max_zoom - 1)
        tile_x, tile_y = lonlat_to_tile(lon, lat, zoom)
        target_lon, target_lat = tile_center(tile_x, tile_y, zoom)

        country_code = None
        choices = None
        mode = AnswerMode(answer_mode)

        if mode.by_country:
            country = await countries_service.at_point(db, target_lon, target_lat)

            # Границы и каталог обязаны сходиться: иначе правильным ответом
            # окажется не та страна, которую игрок увидит в результате. Такие
            # места в режим стран просто не попадают — их единицы
            if country is None or not _same_country(country.name, zone.country):
                logger.info(
                    "Зона %s мимо режима стран: каталог %r, границы %r",
                    zone.name,
                    zone.country,
                    None if country is None else country.name,
                )
                if zone_id is not None:
                    raise NotFoundError(f"Зона {zone.name} не годится для режима стран")
                continue

            country_code = country.code

            if mode is AnswerMode.CHOICE:
                # Список собирается один раз, здесь: у всех, кто играет одну
                # серию, варианты обязаны совпадать — иначе раунд челленджа
                # или комнаты у одного окажется легче, чем у другого
                options = await countries_service.choices_for(
                    db, country_code, target_lon, target_lat
                )

                # Мир маленьким не бывает, но границы могут быть загружены
                # частично: без вариантов режим выбора превращается в одну
                # кнопку с готовым ответом
                if len(options) < countries_service.CHOICES:
                    logger.info("Зона %s мимо режима выбора: мало стран", zone.name)
                    if zone_id is not None:
                        raise NotFoundError(f"Зона {zone.name} не годится для режима выбора")
                    continue

                choices = ",".join(options)

        taken.add(zone.id)

        return SeriesRound(
            position=position,
            zone_id=zone.id,
            target_point=WKTElement(f"POINT({target_lon} {target_lat})", srid=4326),
            country_code=country_code,
            choices=choices,
            tile_zoom=zoom,
            tile_x=tile_x,
            tile_y=tile_y,
            view_extent_km=Decimal(str(round(tile_width_km(tile_x, tile_y, zoom), 3))),
        )

    raise NotFoundError("Не нашлось подходящего места под заданные условия")


def _same_country(border_name: str, catalog_name: str | None) -> bool:
    """Одна ли это страна: названия у границ и у каталога местами разные."""
    if catalog_name is None:
        return False
    return border_name == CATALOG_ALIASES.get(catalog_name, catalog_name)
