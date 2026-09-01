"""
Подсказка в раунде.

Раскрывает самое широкое из того, чего игрок ещё не знает из условий партии:
на всём мире это часть света, внутри выбранной части света — страна, внутри
одной страны — регион. Подсказка, повторяющая условия партии, ничего не
добавляет, и продавать её за очки нечестно — такую сервер просто не выдаёт.

Координат в подсказке нет. Правило то же, что и у активного раунда: до конца
раунда клиент не получает ничего, по чему можно вычислить цель. Название
места ещё нужно найти на карте самому — тем подсказка и отличается от ответа.
"""

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app import messages
from app.exceptions import ConflictError
from app.messages import Message
from app.models.enums import continent_name, group_countries
from app.models.game_session import GameSession
from app.models.location_zone import LocationZone
from app.models.round import Round
from app.models.series import RoundSeries
from app.observability import metrics
from app.services.round_timer import is_late
from app.services.scoring import score_after_hint
from app.utils import zone_names

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Hint:
    """Что раскрыто: подпись поля и его значение."""

    label: str
    value: str


#: Подписи полей подсказки. Игрок их читает, поэтому они знают оба языка
HINT_CONTINENT = Message("Часть света", "Continent")
HINT_COUNTRY = Message("Страна", "Country")
HINT_REGION = Message("Регион", "Region")


def choose(zone: LocationZone, series: RoundSeries | None, language: str) -> Hint | None:
    """
    Самое широкое, чего игрок ещё не знает.

    Части света он не знает, если играет по всему миру; страну — если условия
    партии не сводятся к одной стране. Регион не задаётся условиями никогда,
    поэтому он последний в очереди и всегда что-то добавляет — если он вообще
    заполнен у зоны.
    """
    place_chosen = series is not None and (
        series.continent is not None or series.country_group is not None
    )
    country_chosen = (
        series is not None
        and series.country_group is not None
        and len(group_countries(series.country_group)) == 1
    )

    candidates = (
        (
            not place_chosen,
            HINT_CONTINENT,
            None if zone.continent is None else continent_name(zone.continent, language),
        ),
        (not country_chosen, HINT_COUNTRY, zone_names.country_name(zone.country, language)),
        (True, HINT_REGION, zone_names.place_name(zone.region, language)),
    )

    for unknown, label, value in candidates:
        if unknown and value:
            return Hint(label=label.text(language), value=value)

    return None


async def for_round(db: AsyncSession, round_obj: Round, language: str) -> Hint | None:
    """
    Подсказка этого раунда — та же самая при каждом обращении.

    Зона и серия берутся запросом по идентификатору, а не через связи: раунд
    приходит сюда из разных мест, и полагаться на то, что связь уже загружена,
    значило бы получить обращение к базе в неожиданный момент.
    """
    # В режиме выбора подсказок нет: там под снимком шесть названий, и
    # «это в Африке» вычёркивает половину списка разом. Самый простой режим
    # незачем упрощать ещё раз, да ещё и за очки
    if round_obj.choices:
        return None

    zone = await db.get(LocationZone, round_obj.zone_id)
    if zone is None:
        return None

    session = await db.get(GameSession, round_obj.session_id)
    series = (
        None
        if session is None or session.series_id is None
        else await db.get(RoundSeries, session.series_id)
    )

    return choose(zone, series, language)


async def take(db: AsyncSession, round_obj: Round, language: str) -> Hint:
    """Взять подсказку: раскрыть место и уменьшить максимум очков раунда."""
    if not round_obj.is_open:
        raise ConflictError(messages.ROUND_CLOSED)

    if is_late(round_obj):
        raise ConflictError(messages.ROUND_TIME_OVER)

    if round_obj.hint_used:
        raise ConflictError(messages.HINT_ALREADY_TAKEN)

    hint = await for_round(db, round_obj, language)
    if hint is None:
        raise ConflictError(messages.HINT_ADDS_NOTHING)

    round_obj.hint_used = True
    round_obj.max_score = score_after_hint(round_obj.max_score)
    await db.flush()

    await metrics.count("hint_taken")
    logger.info("Раунд %s: взята подсказка «%s»", round_obj.id, hint.label)

    return hint
