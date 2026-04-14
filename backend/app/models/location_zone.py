from datetime import datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, SmallInteger, String, Text, func, Integer, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ZoneCategory, DifficultyLevel


class LocationZone(Base):
    """
    Полигон на карте, внутри которого алгоритм выбирает случайную точку для раунда.
    Хранится в WGS84 (EPSG:4326).
    """

    __tablename__ = "location_zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Сложность и категория
    difficulty: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1, index=True
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=False, default=ZoneCategory.MIXED, index=True
    )
    
    # Геоданные
    polygon: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326),
        nullable=False,
    )
    center_point: Mapped[Optional[Geometry]] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326)
    )
    area_sq_km: Mapped[Optional[float]] = mapped_column(Float)
    
    # Статистика
    total_rounds: Mapped[int] = mapped_column(Integer, default=0)
    average_score: Mapped[Optional[float]] = mapped_column(Float)
    average_distance: Mapped[Optional[float]] = mapped_column(Float)
    popularity: Mapped[int] = mapped_column(Integer, default=0)  # Сколько раз выбрали
    
    # Метаданные
    country: Mapped[Optional[str]] = mapped_column(String(100))
    region: Mapped[Optional[str]] = mapped_column(String(100))
    tags: Mapped[Optional[str]] = mapped_column(Text)  # JSON список тегов
    thumbnail_url: Mapped[Optional[str]] = mapped_column(Text)
    
    # Флаги
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Связи
    rounds: Mapped[list["Round"]] = relationship(  # noqa: F821
        back_populates="zone", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<LocationZone id={self.id} name={self.name!r} difficulty={self.difficulty}>"
    
    def update_statistics(self) -> None:
        """Обновить статистику зоны на основе завершённых раундов"""
        completed_rounds = [r for r in self.rounds if r.score is not None]
        
        if not completed_rounds:
            return
        
        self.total_rounds = len(completed_rounds)
        
        # Средний счёт
        total_score = sum(r.score for r in completed_rounds)
        self.average_score = total_score / self.total_rounds
        
        # Среднее расстояние
        total_distance = sum(
            float(r.distance_km) for r in completed_rounds 
            if r.distance_km is not None
        )
        self.average_distance = total_distance / self.total_rounds
        
        self.updated_at = datetime.utcnow()
    
    def increment_popularity(self) -> None:
        """Увеличить счётчик популярности"""
        self.popularity += 1
        self.updated_at = datetime.utcnow()
    
    def get_difficulty_name(self) -> str:
        """Получить название уровня сложности"""
        from app.models.enums import EnumUtils
        return EnumUtils.get_difficulty_display_name(self.difficulty)
    
    def get_category_name(self) -> str:
        """Получить название категории"""
        from app.models.enums import EnumUtils
        return EnumUtils.get_category_display_name(self.category)
    
    def get_tags_list(self) -> list[str]:
        """Получить список тегов"""
        if not self.tags:
            return []
        
        import json
        try:
            return json.loads(self.tags)
        except:
            return []
    
    def add_tag(self, tag: str) -> None:
        """Добавить тег"""
        tags = self.get_tags_list()
        if tag not in tags:
            tags.append(tag)
            import json
            self.tags = json.dumps(tags)
    
    def remove_tag(self, tag: str) -> None:
        """Удалить тег"""
        tags = self.get_tags_list()
        if tag in tags:
            tags.remove(tag)
            import json
            self.tags = json.dumps(tags)
    
    def to_dict(self, include_statistics: bool = True) -> dict:
        """Преобразовать зону в словарь"""
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "difficulty": self.difficulty,
            "difficulty_name": self.get_difficulty_name(),
            "category": self.category,
            "category_name": self.get_category_name(),
            "country": self.country,
            "region": self.region,
            "tags": self.get_tags_list(),
            "thumbnail_url": self.thumbnail_url,
            "is_active": self.is_active,
            "is_featured": self.is_featured,
            "is_premium": self.is_premium,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_statistics:
            result.update({
                "total_rounds": self.total_rounds,
                "average_score": self.average_score,
                "average_distance": self.average_distance,
                "popularity": self.popularity,
                "area_sq_km": self.area_sq_km,
            })
        
        return result
    
    def get_bounds(self) -> Optional[tuple[float, float, float, float]]:
        """Получить границы зоны (min_lng, min_lat, max_lng, max_lat)"""
        # В реальной реализации нужно использовать PostGIS функции
        # Это упрощённая версия
        try:
            # Предполагаем, что polygon хранится как WKT
            # В реальности нужно парсить WKT или использовать ST_Extent
            return (-180.0, -90.0, 180.0, 90.0)  # Заглушка
        except:
            return None
