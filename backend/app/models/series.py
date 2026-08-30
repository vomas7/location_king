from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import AnswerMode


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

    # Условия, из которых собрана серия. Нужны таблице лидеров: она делится
    # по ним, а больше эти значения нигде не хранятся. Пусто — серия собрана
    # до того, как условия начали запоминать, либо без ограничений
    difficulty: Mapped[str | None] = mapped_column(String(20))
    continent: Mapped[str | None] = mapped_column(String(20))
    country_group: Mapped[str | None] = mapped_column(String(20))

    #: Чем отвечают на раунды этой серии — точкой или страной
    answer_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=AnswerMode.POINT,
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

    #: Страна цели по границам. Считается один раз при сборке серии: у всех,
    #: кто играет эту серию, правильный ответ обязан быть один
    country_code: Mapped[str | None] = mapped_column(String(3))

    #: Варианты ответа для режима выбора: коды стран через запятую, среди них
    #: правильный. Собираются один раз при сборке серии — у всех, кто играет
    #: одну серию, список обязан быть одним и тем же, иначе раунды несравнимы
    choices: Mapped[str | None] = mapped_column(String(80))

    tile_zoom: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    tile_x: Mapped[int] = mapped_column(Integer, nullable=False)
    tile_y: Mapped[int] = mapped_column(Integer, nullable=False)
    view_extent_km: Mapped[Numeric] = mapped_column(Numeric(8, 3), nullable=False)

    series: Mapped["RoundSeries"] = relationship(back_populates="rounds")

    def __repr__(self) -> str:
        return f"<SeriesRound series={self.series_id} position={self.position}>"
