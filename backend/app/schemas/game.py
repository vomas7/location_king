"""
Схемы игрового API.

Ключевое правило: в схемах активного раунда нет ни одного поля с координатами
цели. Они появляются только в RoundResult, то есть после принятой догадки.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class StartSessionRequest(BaseModel):
    """Параметры новой партии."""

    rounds_total: int = Field(default=5, ge=1, le=20)
    view_extent_km: float = Field(
        default=5.0,
        gt=0.2,
        le=200.0,
        description="Желаемый размер показываемой области в километрах",
    )
    difficulty: int | None = Field(default=None, ge=1, le=5)
    category: str | None = None
    zone_id: int | None = None


class GuessRequest(BaseModel):
    """Догадка игрока."""

    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)


class ZoneView(BaseModel):
    """Зона. Отдаётся в списке зон и в результатах завершённого раунда."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    difficulty: int
    difficulty_name: str
    category: str
    category_name: str
    country: str | None
    region: str | None
    tags: list[str] = Field(default_factory=list)


class RoundView(BaseModel):
    """
    Активный раунд глазами клиента.

    Никаких координат: снимок доступен только через tiles_url.
    """

    id: int
    index: int
    status: str
    view_extent_km: Decimal
    max_zoom: int
    tiles_url: str
    attribution: str
    created_at: datetime


class RoundResult(BaseModel):
    """Завершённый раунд: здесь цель уже можно показать."""

    id: int
    index: int
    status: str
    view_extent_km: Decimal
    target: tuple[float, float]
    guess: tuple[float, float] | None
    distance_km: Decimal | None
    score: int
    max_score: int
    accuracy: Decimal | None
    zone: ZoneView
    guessed_at: datetime | None


class SessionView(BaseModel):
    """Состояние партии."""

    id: str
    status: str
    #: Заполнено, если партия относится к челленджу этого дня
    challenge_day: date | None
    rounds_total: int
    rounds_done: int
    total_score: int
    average_score: float | None
    started_at: datetime
    finished_at: datetime | None


class SessionStateResponse(BaseModel):
    """Партия вместе с текущим раундом и историей завершённых."""

    session: SessionView
    current_round: RoundView | None
    results: list[RoundResult]


class GuessResponse(BaseModel):
    """Результат догадки и следующий шаг."""

    result: RoundResult
    session: SessionView
    next_round: RoundView | None
    is_session_finished: bool


class SessionSummary(BaseModel):
    """Партия в списке истории — без раундов."""

    id: str
    status: str
    challenge_day: date | None
    rounds_total: int
    rounds_done: int
    total_score: int
    started_at: datetime
    finished_at: datetime | None


class SessionHistoryResponse(BaseModel):
    """Страница истории партий игрока."""

    sessions: list[SessionSummary]
    total: int
