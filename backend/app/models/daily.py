from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DailyChallenge(Base):
    """
    Челлендж дня: серия раундов, одинаковая для всех.

    Сама последовательность лежит в round_series — там же, где серия комнаты
    мультиплеера. Здесь только привязка к дню.
    """

    __tablename__ = "daily_challenges"

    day: Mapped[date] = mapped_column(Date, primary_key=True)

    series_id: Mapped[int] = mapped_column(
        ForeignKey("round_series.id", ondelete="CASCADE"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    series: Mapped["RoundSeries"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return f"<DailyChallenge day={self.day}>"
