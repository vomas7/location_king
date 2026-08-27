import json
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Float, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ZoneCategory


class LocationZone(Base):
    """
    Полигон, внутри которого выбирается точка для раунда.

    Хранится в WGS84 (EPSG:4326).
    """

    __tablename__ = "location_zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)

    difficulty: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1, index=True)
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default=ZoneCategory.MIXED,
        index=True,
    )

    polygon: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326),
        nullable=False,
    )

    continent: Mapped[str | None] = mapped_column(String(20), index=True)
    country: Mapped[str | None] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(100))
    tags: Mapped[str | None] = mapped_column(Text)  # JSON-список строк

    total_rounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_score: Mapped[float | None] = mapped_column(Float)
    average_distance: Mapped[float | None] = mapped_column(Float)
    popularity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    rounds: Mapped[list["Round"]] = relationship(back_populates="zone", lazy="select")  # noqa: F821

    def __repr__(self) -> str:
        return f"<LocationZone id={self.id} name={self.name!r} difficulty={self.difficulty}>"

    @property
    def tag_list(self) -> list[str]:
        """Теги зоны. Некорректный JSON в этом поле — данные, а не сбой."""
        if not self.tags:
            return []
        try:
            return json.loads(self.tags)
        except json.JSONDecodeError:
            return []
