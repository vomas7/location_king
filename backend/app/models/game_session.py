from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import SessionStatus


class GameSession(Base):
    """Партия из нескольких раундов."""

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

    # Заполнено — партия идёт по заготовленной серии, а не по случайным зонам
    series_id: Mapped[int | None] = mapped_column(
        ForeignKey("round_series.id", ondelete="SET NULL"),
    )

    # Заполнено — партия относится к челленджу этого дня. Уникальный индекс не
    # даёт сыграть челлендж дважды.
    challenge_day: Mapped[date | None] = mapped_column(Date, index=True)

    # Заполнено — партия сыграна в комнате мультиплеера
    match_code: Mapped[str | None] = mapped_column(
        ForeignKey("matches.code", ondelete="SET NULL"),
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=SessionStatus.ACTIVE,
        index=True,
    )

    #: Сколько секунд даётся на раунд. NULL — без ограничения
    time_limit_seconds: Mapped[int | None] = mapped_column(SmallInteger)

    rounds_total: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=5)
    rounds_done: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_score: Mapped[float | None] = mapped_column(Float)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="sessions")  # noqa: F821
    rounds: Mapped[list["Round"]] = relationship(  # noqa: F821
        back_populates="session",
        lazy="select",
        order_by="Round.position",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<GameSession id={self.id} status={self.status!r} score={self.total_score}>"

    @property
    def is_active(self) -> bool:
        return self.status == SessionStatus.ACTIVE
