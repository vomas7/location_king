from datetime import datetime
from decimal import Decimal
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, func, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import RoundStatus, ScoreTier
from app.utils.geometry_utils import CoordinateUtils


class Round(Base):
    __tablename__ = "rounds"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Связи
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    zone_id: Mapped[int] = mapped_column(
        ForeignKey("location_zones.id"), nullable=False
    )

    # Геоданные
    target_point: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=False,
    )
    guess_point: Mapped[Optional[Geometry]] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
    )
    
    # Статус и результаты
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RoundStatus.PENDING
    )
    distance_km: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    score: Mapped[int] = mapped_column(Integer, default=0)
    accuracy_percentage: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))
    
    # Параметры раунда
    view_extent_km: Mapped[int] = mapped_column(SmallInteger, default=5)
    time_limit_seconds: Mapped[Optional[int]] = mapped_column(SmallInteger)
    max_score: Mapped[int] = mapped_column(Integer, default=5000)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    guessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Метаданные
    satellite_image_url: Mapped[Optional[str]] = mapped_column(Text)
    hint_used: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Связи
    session: Mapped["GameSession"] = relationship(back_populates="rounds")  # noqa: F821
    zone: Mapped["LocationZone"] = relationship(back_populates="rounds")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Round id={self.id} score={self.score} distance_km={self.distance_km}>"
    
    def start(self) -> None:
        """Начать раунд"""
        if self.status == RoundStatus.PENDING:
            self.status = RoundStatus.ACTIVE
            self.started_at = datetime.utcnow()
    
    def submit_guess(self, guess_lng: float, guess_lat: float) -> None:
        """Отправить догадку"""
        from geoalchemy2 import WKTElement
        
        if self.status != RoundStatus.ACTIVE:
            raise ValueError("Round is not active")
        
        # Сохраняем догадку
        self.guess_point = WKTElement(f"POINT({guess_lng} {guess_lat})", srid=4326)
        self.guessed_at = datetime.utcnow()
        
        # Вычисляем расстояние
        target_coords = self.get_target_coordinates()
        self.distance_km = Decimal(str(CoordinateUtils.calculate_distance_haversine(
            guess_lng, guess_lat,
            target_coords[0], target_coords[1]
        )))
        
        # Вычисляем очки
        self.score = self.calculate_score()
        
        # Вычисляем точность
        self.accuracy_percentage = self.calculate_accuracy()
        
        # Обновляем статус
        self.status = RoundStatus.GUESSED
        self.completed_at = datetime.utcnow()
    
    def skip(self) -> None:
        """Пропустить раунд"""
        if self.status in [RoundStatus.PENDING, RoundStatus.ACTIVE]:
            self.status = RoundStatus.SKIPPED
            self.completed_at = datetime.utcnow()
    
    def timeout(self) -> None:
        """Завершить раунд по таймауту"""
        if self.status == RoundStatus.ACTIVE:
            self.status = RoundStatus.TIMED_OUT
            self.completed_at = datetime.utcnow()
    
    def calculate_score(self) -> int:
        """Вычислить очки на основе расстояния"""
        if self.distance_km is None:
            return 0
        
        distance = float(self.distance_km)
        max_distance = self.view_extent_km * 2  # Максимальное расстояние для получения очков
        
        if distance >= max_distance:
            return 0
        
        # Формула: score = max_score * (1 - (distance / max_distance)^2)
        # Квадратичная зависимость для большего штрафа за большие расстояния
        ratio = distance / max_distance
        score = int(self.max_score * (1 - ratio ** 2))
        
        # Округляем до ближайших 10
        score = (score // 10) * 10
        
        return max(0, min(self.max_score, score))
    
    def calculate_accuracy(self) -> Optional[float]:
        """Вычислить точность в процентах"""
        if self.distance_km is None or self.view_extent_km == 0:
            return None
        
        distance = float(self.distance_km)
        max_distance = self.view_extent_km * 2
        
        if distance >= max_distance:
            return 0.0
        
        accuracy = (1 - (distance / max_distance)) * 100
        return round(accuracy, 2)
    
    def get_target_coordinates(self) -> tuple[float, float]:
        """Получить координаты цели"""
        if hasattr(self.target_point, 'x') and hasattr(self.target_point, 'y'):
            return self.target_point.x, self.target_point.y
        
        # Если geometry объект не имеет атрибутов x, y
        # (зависит от того, как geoalchemy2 возвращает данные)
        try:
            from sqlalchemy import text
            # Это упрощённый пример, в реальности нужно адаптировать
            return 0.0, 0.0
        except:
            return 0.0, 0.0
    
    def get_guess_coordinates(self) -> Optional[tuple[float, float]]:
        """Получить координаты догадки"""
        if not self.guess_point:
            return None
        
        if hasattr(self.guess_point, 'x') and hasattr(self.guess_point, 'y'):
            return self.guess_point.x, self.guess_point.y
        
        return None
    
    def get_score_tier(self) -> ScoreTier:
        """Получить уровень очков"""
        from app.models.enums import EnumUtils
        return EnumUtils.get_score_tier(self.score)
    
    def get_duration_seconds(self) -> Optional[float]:
        """Получить продолжительность раунда в секундах""""
        if not self.started_at:
            return None
        
        end_time = self.completed_at or datetime.utcnow()
        duration = end_time - self.started_at
        return duration.total_seconds()
    
    def is_completed(self) -> bool:
        """Проверить, завершён ли раунд"""
        return self.status in [
            RoundStatus.GUESSED,
            RoundStatus.SKIPPED,
            RoundStatus.TIMED_OUT
        ]
    
    def is_active(self) -> bool:
        """Проверить, активен ли раунд"""
        return self.status == RoundStatus.ACTIVE
    
    def is_pending(self) -> bool:
        """Проверить, ожидает ли раунд начала"""
        return self.status == RoundStatus.PENDING
    
    def to_dict(self) -> dict:
        """Преобразовать раунд в словарь"""
        target_coords = self.get_target_coordinates()
        guess_coords = self.get_guess_coordinates()
        
        return {
            "id": self.id,
            "session_id": self.session_id,
            "zone_id": self.zone_id,
            "status": self.status,
            "target_point": target_coords,
            "guess_point": guess_coords,
            "distance_km": float(self.distance_km) if self.distance_km else None,
            "score": self.score,
            "accuracy_percentage": float(self.accuracy_percentage) if self.accuracy_percentage else None,
            "view_extent_km": self.view_extent_km,
            "time_limit_seconds": self.time_limit_seconds,
            "max_score": self.max_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "guessed_at": self.guessed_at.isoformat() if self.guessed_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "satellite_image_url": self.satellite_image_url,
            "hint_used": self.hint_used,
            "notes": self.notes,
            "score_tier": self.get_score_tier().value,
            "duration_seconds": self.get_duration_seconds(),
            "is_completed": self.is_completed(),
            "is_active": self.is_active(),
            "is_pending": self.is_pending(),
            "zone": {
                "id": self.zone.id,
                "name": self.zone.name,
                "difficulty": self.zone.difficulty,
                "category": self.zone.category,
            } if self.zone else None,
        }
