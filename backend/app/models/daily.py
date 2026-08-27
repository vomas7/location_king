from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, SmallInteger, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DailyChallenge(Base):
    """
    Серия раундов на сутки, одинаковая для всех игроков.

    Создаётся при первом обращении за день и дальше не меняется: иначе двое,
    начавшие игру в разное время, получили бы разные места.
    """

    __tablename__ = "daily_challenges"

    day: Mapped[date] = mapped_column(Date, primary_key=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    rounds: Mapped[list["DailyRound"]] = relationship(
        back_populates="challenge",
        lazy="select",
        order_by="DailyRound.position",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<DailyChallenge day={self.day}>"


class DailyRound(Base):
    """Заготовка раунда челленджа: из неё игроку копируется настоящий раунд."""

    __tablename__ = "daily_rounds"

    id: Mapped[int] = mapped_column(primary_key=True)

    day: Mapped[date] = mapped_column(
        ForeignKey("daily_challenges.day", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    zone_id: Mapped[int] = mapped_column(ForeignKey("location_zones.id"), nullable=False)
    target_point: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=False,
    )

    tile_zoom: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    tile_x: Mapped[int] = mapped_column(Integer, nullable=False)
    tile_y: Mapped[int] = mapped_column(Integer, nullable=False)
    view_extent_km: Mapped[Numeric] = mapped_column(Numeric(8, 3), nullable=False)

    challenge: Mapped["DailyChallenge"] = relationship(back_populates="rounds")

    def __repr__(self) -> str:
        return f"<DailyRound day={self.day} position={self.position}>"
