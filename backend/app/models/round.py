from datetime import datetime
from decimal import Decimal

from geoalchemy2 import Geometry
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import RoundStatus


class Round(Base):
    """
    Один раунд: игроку показывают участок снимка, он ставит точку на карте.

    Участок — это ровно один тайл Web Mercator (tile_zoom/tile_x/tile_y) и его
    потомки. Цель раунда — центр этого тайла. Номера тайла клиенту не
    отдаются: снимок он получает через прокси по локальным координатам.
    """

    __tablename__ = "rounds"

    id: Mapped[int] = mapped_column(primary_key=True)

    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    zone_id: Mapped[int] = mapped_column(ForeignKey("location_zones.id"), nullable=False)

    #: Номер раунда внутри партии, начиная с единицы
    position: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    target_point: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=False,
    )
    guess_point: Mapped[Geometry | None] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
    )

    # Тайл, который показывается игроку
    tile_zoom: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    tile_x: Mapped[int] = mapped_column(Integer, nullable=False)
    tile_y: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default=RoundStatus.ACTIVE)
    distance_km: Mapped[Decimal | None] = mapped_column(Numeric(10, 3))
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accuracy_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    view_extent_km: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, nullable=False, default=5000)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    #: До какого момента принимается ответ. NULL — время не ограничено
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    guessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    #: Сколько секунд игрок думал — для статистики и текста результата
    answer_seconds: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))

    session: Mapped["GameSession"] = relationship(back_populates="rounds")  # noqa: F821
    zone: Mapped["LocationZone"] = relationship(back_populates="rounds")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Round id={self.id} status={self.status!r} score={self.score}>"

    @property
    def is_guessed(self) -> bool:
        return self.status == RoundStatus.GUESSED

    @property
    def is_open(self) -> bool:
        """Раунд ещё ждёт ответа."""
        return self.status == RoundStatus.ACTIVE
