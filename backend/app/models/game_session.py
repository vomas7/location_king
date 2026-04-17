from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import GameMode, SessionStatus, TimeControl


class GameSession(Base):
    __tablename__ = "game_sessions"

    # UUID генерируется на стороне PostgreSQL
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Основные параметры игры
    mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=GameMode.SOLO,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SessionStatus.ACTIVE,
        index=True,
    )
    time_control: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TimeControl.UNLIMITED,
    )

    # Статистика игры
    rounds_total: Mapped[int] = mapped_column(SmallInteger, default=5)
    rounds_done: Mapped[int] = mapped_column(SmallInteger, default=0)
    total_score: Mapped[int] = mapped_column(Integer, default=0)
    average_score: Mapped[float | None] = mapped_column(
        Float,
        default=0.0,
    )
    best_round_score: Mapped[int] = mapped_column(Integer, default=0)
    worst_round_score: Mapped[int] = mapped_column(Integer, default=0)

    # Время игры
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Метаданные
    title: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    is_public: Mapped[bool] = mapped_column(default=False)
    allow_comments: Mapped[bool] = mapped_column(default=True)

    # Связи
    user: Mapped["User"] = relationship(back_populates="sessions")  # noqa: F821
    rounds: Mapped[list["Round"]] = relationship(  # noqa: F821
        back_populates="session",
        lazy="select",
        order_by="Round.created_at",
    )

    def __repr__(self) -> str:
        return f"<GameSession id={self.id} user_id={self.user_id} status={self.status!r}>"

    def update_statistics(self) -> None:
        """Обновить статистику сессии на основе завершённых раундов"""
        completed_rounds = [r for r in self.rounds if r.score is not None]

        if not completed_rounds:
            return

        # Обновляем общий счёт
        self.total_score = sum(r.score for r in completed_rounds)

        # Обновляем средний счёт
        self.average_score = self.total_score / len(completed_rounds)

        # Обновляем лучший/худший раунды
        self.best_round_score = max(r.score for r in completed_rounds)
        self.worst_round_score = min(r.score for r in completed_rounds)

        # Обновляем количество завершённых раундов
        self.rounds_done = len(completed_rounds)

        # Обновляем время последней активности
        self.last_activity_at = datetime.utcnow()

    def get_completion_percentage(self) -> float:
        """Получить процент завершения сессии"""
        if self.rounds_total == 0:
            return 0.0
        return (self.rounds_done / self.rounds_total) * 100

    def get_average_distance(self) -> float | None:
        """Получить среднее расстояние по завершённым раундам"""
        completed_rounds = [r for r in self.rounds if r.distance_km is not None]

        if not completed_rounds:
            return None

        total_distance = sum(float(r.distance_km) for r in completed_rounds)
        return total_distance / len(completed_rounds)

    def get_duration_seconds(self) -> float | None:
        """Получить продолжительность сессии в секундах"""
        if not self.started_at:
            return None

        end_time = self.finished_at or datetime.utcnow()
        duration = end_time - self.started_at
        return duration.total_seconds()

    def get_time_per_round(self) -> float | None:
        """Получить среднее время на раунд в секундах"""
        duration = self.get_duration_seconds()
        if duration is None or self.rounds_done == 0:
            return None

        return duration / self.rounds_done

    def is_active(self) -> bool:
        """Проверить, активна ли сессия"""
        return self.status == SessionStatus.ACTIVE

    def is_finished(self) -> bool:
        """Проверить, завершена ли сессия"""
        return self.status in [SessionStatus.FINISHED, SessionStatus.ABANDONED]

    def finish(self, status: SessionStatus = SessionStatus.FINISHED) -> None:
        """Завершить сессию"""
        self.status = status
        self.finished_at = datetime.utcnow()
        self.update_statistics()

    def abandon(self) -> None:
        """Бросить сессию"""
        self.finish(SessionStatus.ABANDONED)

    def pause(self) -> None:
        """Приостановить сессию"""
        if self.is_active():
            self.status = SessionStatus.PAUSED

    def resume(self) -> None:
        """Возобновить сессию"""
        if self.status == SessionStatus.PAUSED:
            self.status = SessionStatus.ACTIVE

    def to_dict(self, include_rounds: bool = False) -> dict:
        """Преобразовать сессию в словарь"""
        result = {
            "id": self.id,
            "user_id": self.user_id,
            "mode": self.mode,
            "status": self.status,
            "time_control": self.time_control,
            "rounds_total": self.rounds_total,
            "rounds_done": self.rounds_done,
            "total_score": self.total_score,
            "average_score": self.average_score,
            "best_round_score": self.best_round_score,
            "worst_round_score": self.worst_round_score,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "last_activity_at": self.last_activity_at.isoformat()
            if self.last_activity_at
            else None,
            "title": self.title,
            "description": self.description,
            "is_public": self.is_public,
            "allow_comments": self.allow_comments,
            "completion_percentage": self.get_completion_percentage(),
            "average_distance": self.get_average_distance(),
            "duration_seconds": self.get_duration_seconds(),
            "time_per_round": self.get_time_per_round(),
            "is_active": self.is_active(),
            "is_finished": self.is_finished(),
        }

        if include_rounds:
            result["rounds"] = [r.to_dict() for r in self.rounds]

        return result
