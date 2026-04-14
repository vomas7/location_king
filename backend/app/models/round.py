from datetime import datetime
from decimal import Decimal

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, SmallInteger, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Round(Base):
    __tablename__ = "rounds"

    id: Mapped[int] = mapped_column(primary_key=True)

    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    zone_id: Mapped[int] = mapped_column(
        ForeignKey("location_zones.id"), nullable=False
    )

    # Правильный ответ — хранится только на сервере, клиент не получает до гесса
    target_point: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=False,
    )

    # Ответ пользователя — заполняется после гесса
    guess_point: Mapped[Geometry | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
    )

    # Считается через ST_DistanceSphere на стороне БД
    distance_km: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    score: Mapped[int] = mapped_column(Integer, default=0)

    # Размер экстента снимка, показанного пользователю (в км)
    view_extent_km: Mapped[int] = mapped_column(SmallInteger, default=500)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    guessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Связи
    session: Mapped["GameSession"] = relationship(back_populates="rounds")  # noqa: F821
    zone: Mapped["LocationZone"] = relationship(back_populates="rounds")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Round id={self.id} score={self.score} distance_km={self.distance_km}>"
