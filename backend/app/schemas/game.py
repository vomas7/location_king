"""
Схемы игрового API.

Ключевое правило: в схемах активного раунда нет ни одного поля с координатами
цели. Они появляются только в RoundResult, то есть после принятой догадки.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import AnswerMode, Continent, CountryGroup, Difficulty
from app.services import difficulty as difficulty_service
from app.services.round_timer import ALLOWED_TIME_LIMITS
from app.services.series import MAX_ROUNDS, MIN_ROUNDS


class RoundsRequest(BaseModel):
    """
    Условия набора раундов.

    Одинаковы для обычной партии и для комнаты мультиплеера, поэтому описаны
    один раз.
    """

    rounds_total: int = Field(default=5, ge=MIN_ROUNDS, le=MAX_ROUNDS)
    #: Ширина кадра. Пусто — берётся из уровня: игрок её больше не выбирает,
    #: и два независимых регулятора сложности сводились в бессмысленную пару
    view_extent_km: float | None = Field(
        default=None,
        gt=0.2,
        le=200.0,
        description="Размер показываемой области в километрах. Пусто — по уровню",
    )
    category: str | None = None
    continent: Continent | None = None
    country_group: CountryGroup | None = None
    difficulty: Difficulty = Difficulty.NORMAL
    #: Чем отвечать: точкой на карте или названием страны
    answer_mode: AnswerMode = AnswerMode.POINT
    time_limit_seconds: int | None = Field(
        default=None,
        description="Сколько секунд даётся на раунд. Пусто — без ограничения",
    )

    @field_validator("time_limit_seconds")
    @classmethod
    def check_time_limit(cls, value: int | None) -> int | None:
        """Произвольные значения не принимаем: режимы должны быть сравнимы."""
        if value is not None and value not in ALLOWED_TIME_LIMITS:
            allowed = ", ".join(str(item) for item in ALLOWED_TIME_LIMITS)
            raise ValueError(f"Допустимые значения: {allowed}")
        return value

    @property
    def frame_km(self) -> float:
        """Ширина кадра для этих условий: своя или выведенная из уровня."""
        if self.view_extent_km is not None:
            return self.view_extent_km

        return difficulty_service.view_extent_km(self.difficulty)

    @model_validator(mode="after")
    def check_country_mode(self) -> "RoundsRequest":
        """
        Страна в условиях партии — это и есть ответ на её раунды.

        Интерфейс такой выбор не предлагает, но запрос можно собрать и руками,
        а очки из такой партии попадут в общую таблицу лидеров.
        """
        if AnswerMode(self.answer_mode).by_country and self.country_group is not None:
            raise ValueError("В режиме стран нельзя выбирать страну: это ответ на все раунды")
        return self


class StartSessionRequest(RoundsRequest):
    """Параметры новой партии."""

    #: Играть именно в этой зоне. Пусто — зоны выбираются случайно
    zone_id: int | None = None


class GuessRequest(BaseModel):
    """
    Догадка игрока: точка на карте или страна, смотря о чём был раунд.

    Чем именно отвечают, решает раунд, а не запрос, поэтому сверку с режимом
    делает сервис. Здесь проверяется только то, что ответ ровно один: запрос
    и с точкой, и со страной означает ошибку в клиенте.
    """

    longitude: float | None = Field(default=None, ge=-180, le=180)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    #: Код страны ISO 3166-1 alpha-3, если раунд про страны
    country: str | None = Field(default=None, min_length=3, max_length=3)

    @property
    def point(self) -> tuple[float, float] | None:
        """Точка догадки, если она есть."""
        if self.longitude is None or self.latitude is None:
            return None
        return self.longitude, self.latitude

    @model_validator(mode="after")
    def check_single_answer(self) -> "GuessRequest":
        if (self.point is None) == (self.country is None):
            raise ValueError("Ответ — либо точка на карте, либо страна")
        return self


class ZoneView(BaseModel):
    """Зона. Отдаётся в списке зон и в результатах завершённого раунда."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    category: str
    category_name: str
    continent: str | None
    continent_name: str
    country: str | None
    region: str | None
    tags: list[str] = Field(default_factory=list)

    #: Сколько раз зона сыграна всеми игроками и какой у них средний промах.
    #: Нужно, чтобы игрок видел свой результат не в пустоте: «промахнулся на
    #: 340 км» само по себе ничего не говорит
    total_rounds: int
    average_distance: float | None


class HintView(BaseModel):
    """
    Раскрытая подсказка: подпись поля и его значение.

    Координат здесь нет и быть не может — только название места, которое ещё
    нужно найти на карте самому.
    """

    label: str
    value: str


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
    #: Чем отвечать на этот раунд
    answer_mode: AnswerMode
    #: Варианты для режима выбора: название и код, среди них верный. Пусто в
    #: остальных режимах. Что именно верно, здесь не сказано — иначе ответ
    #: приезжал бы вместе с вопросом
    choices: list["CountryChoice"] = []
    #: Сколько очков ещё можно взять за раунд. Подсказка это число уменьшает
    max_score: int
    #: Заполнено, если игрок взял подсказку
    hint: HintView | None
    #: Во сколько очков обойдётся подсказка. Ноль — брать её нечего или уже
    #: взята: цену считает сервер, клиенту незачем знать формулу
    hint_cost: int
    #: До какого момента принимается ответ. Пусто — время не ограничено
    deadline_at: datetime | None


class CountryChoice(BaseModel):
    """Один вариант ответа в режиме выбора."""

    code: str
    name: str


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
    #: Страна цели и страна, куда попал игрок. Заполнены только в режиме
    #: стран: в обычном раунде вопрос был не про страну
    country: str | None
    guess_country: str | None
    #: Сколько секунд игрок думал над раундом
    answer_seconds: Decimal | None
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
    #: Сколько секунд даётся на раунд. Пусто — без ограничения
    time_limit_seconds: int | None
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
