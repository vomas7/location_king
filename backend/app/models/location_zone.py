from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LocationZone(Base):
    """
    Полигон на карте, внутри которого алгоритм выбирает случайную точку для раунда.
    Хранится в WGS84 (EPSG:4326).
    """

    __tablename__ = "location_zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # 1 = очень легко (крупный город), 5 = очень сложно (глушь / однообразный ландшафт)
    difficulty: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)

    # 'city' | 'nature' | 'architecture' | 'desert' | 'coast' и т.д.
    category: Mapped[str | None] = mapped_column(String(100), index=True)

    # PostGIS POLYGON в WGS84
    polygon: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Связи
    rounds: Mapped[list["Round"]] = relationship(  # noqa: F821
        back_populates="zone", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<LocationZone id={self.id} name={self.name!r} difficulty={self.difficulty}>"
