"""
Pydantic схемы для игрового API.
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

# ============================================================================
# Запросы (Request schemas)
# ============================================================================


class StartSessionRequest(BaseModel):
    """Запрос на начало новой игровой сессии"""

    zone_id: int | None = Field(
        None,
        description="ID конкретной зоны. Если не указан, будет выбрана случайная зона.",
    )
    difficulty: int | None = Field(
        None,
        ge=1,
        le=5,
        description="Сложность зоны (1-5). Используется если zone_id не указан.",
    )
    category: str | None = Field(
        None,
        description="Категория зоны. Используется если zone_id не указан.",
    )
    rounds_total: int = Field(
        5,
        ge=1,
        le=20,
        description="Общее количество раундов в сессии (1-20).",
    )
    view_extent_km: int = Field(
        5,
        ge=1,
        le=50,
        description="Размер видимой области в километрах (1-50).",
    )


class SubmitGuessRequest(BaseModel):
    """Запрос на отправку догадки"""

    longitude: float = Field(
        ...,
        ge=-180,
        le=180,
        description="Долгота выбранной точки",
    )
    latitude: float = Field(
        ...,
        ge=-90,
        le=90,
        description="Широта выбранной точки",
    )


# ============================================================================
# Ответы (Response schemas)
# ============================================================================


class ZoneResponse(BaseModel):
    """Информация о зоне"""

    id: int
    name: str
    description: str | None
    difficulty: int
    category: str | None = None

    class Config:
        from_attributes = True


class RoundResponse(BaseModel):
    """Информация о раунде"""

    id: int
    zone: ZoneResponse
    satellite_image_url: str
    view_extent_km: int
    created_at: datetime

    # Поля, которые заполняются после отправки догадки
    guess_point: tuple[float, float] | None = None
    distance_km: Decimal | None = None
    score: int | None = None
    guessed_at: datetime | None = None

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    """Информация об игровой сессии"""

    id: str
    mode: str
    status: str
    rounds_total: int
    rounds_done: int
    total_score: int
    started_at: datetime
    finished_at: datetime | None

    # Текущий активный раунд (если есть)
    current_round: RoundResponse | None = None

    class Config:
        from_attributes = True


class GuessResponse(BaseModel):
    """Результат отправки догадки"""

    round_id: int
    session_id: str
    distance_km: Decimal
    score: int
    total_session_score: int
    rounds_done: int
    rounds_total: int

    # Координаты правильной точки (показываются после гесса)
    target_point: tuple[float, float]

    # Информация для следующего раунда (если есть)
    next_round: RoundResponse | None = None
    is_session_finished: bool = False


class ScoreboardEntry(BaseModel):
    """Запись в таблице лидеров"""

    username: str
    total_score: int
    games_played: int
    average_score: float


# ============================================================================
# Вспомогательные схемы
# ============================================================================


class HealthResponse(BaseModel):
    """Ответ health check"""

    status: str
    service: str
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    """Схема для ошибок API"""

    detail: str
    error_code: str | None = None
