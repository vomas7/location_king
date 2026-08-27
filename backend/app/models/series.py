from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, SmallInteger, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RoundSeries(Base):
    """
    Заранее заготовленная последовательность раундов.

    Одна и та же для всех, кто её играет: так результаты можно сравнивать.
    На неё ссылаются и челлендж дня, и комната мультиплеера — раньше у каждого
    была своя копия одного и того же.
    """

    __tablename__ = "round_series"

    id: Mapped[int] = mapped_column(primary_key=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    rounds: Mapped[list["SeriesRound"]] = relationship(
        back_populates="series",
        lazy="select",
        order_by="SeriesRound.position",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<RoundSeries id={self.id}>"


class SeriesRound(Base):
    """Заготовка раунда: из неё игроку копируется настоящий раунд."""

    __tablename__ = "series_rounds"

    id: Mapped[int] = mapped_column(primary_key=True)

    series_id: Mapped[int] = mapped_column(
        ForeignKey("round_series.id", ondelete="CASCADE"),
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

    series: Mapped["RoundSeries"] = relationship(back_populates="rounds")

    def __repr__(self) -> str:
        return f"<SeriesRound series={self.series_id} position={self.position}>"
