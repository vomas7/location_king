from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import MatchKind, MatchStatus


class Match(Base):
    """
    Комната мультиплеера.

    Все участники играют одну и ту же серию раундов и в конце сравнивают
    результаты. Код комнаты короткий: его удобно передать голосом.
    """

    __tablename__ = "matches"

    code: Mapped[str] = mapped_column(String(8), primary_key=True)

    host_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    series_id: Mapped[int] = mapped_column(
        ForeignKey("round_series.id", ondelete="CASCADE"),
        nullable=False,
    )

    rounds_total: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    time_limit_seconds: Mapped[int | None] = mapped_column(SmallInteger)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default=MatchStatus.OPEN)

    #: Обычная комната или дуэль из подбора. По итогу дуэли меняется рейтинг
    kind: Mapped[str] = mapped_column(
        String(20), nullable=False, default=MatchKind.ROOM, index=True
    )
    #: Когда по дуэли начислили рейтинг. Пусто — ещё не начисляли, и это
    #: единственная защита от двойного начисления
    rated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    host: Mapped["User"] = relationship()  # noqa: F821
    series: Mapped["RoundSeries"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return f"<Match code={self.code!r} status={self.status!r}>"
