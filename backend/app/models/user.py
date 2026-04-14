from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, String, Integer, Float, Boolean, func, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Идентификация
    keycloak_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), unique=True, nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Статистика
    total_score: Mapped[int] = mapped_column(BigInteger, default=0)
    games_played: Mapped[int] = mapped_column(Integer, default=0)
    games_won: Mapped[int] = mapped_column(Integer, default=0)
    total_rounds: Mapped[int] = mapped_column(Integer, default=0)
    average_score: Mapped[Optional[float]] = mapped_column(Float)
    average_distance: Mapped[Optional[float]] = mapped_column(Float)
    best_score: Mapped[int] = mapped_column(Integer, default=0)
    worst_score: Mapped[int] = mapped_column(Integer, default=0)
    
    # Рейтинги
    elo_rating: Mapped[int] = mapped_column(Integer, default=1000)
    rank: Mapped[Optional[str]] = mapped_column(String(50))
    level: Mapped[int] = mapped_column(Integer, default=1)
    experience: Mapped[int] = mapped_column(Integer, default=0)
    
    # Настройки
    avatar_url: Mapped[Optional[str]] = mapped_column(Text)
    bio: Mapped[Optional[str]] = mapped_column(Text)
    country: Mapped[Optional[str]] = mapped_column(String(100))
    timezone: Mapped[Optional[str]] = mapped_column(String(50))
    language: Mapped[str] = mapped_column(String(10), default="ru")
    
    # Флаги
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Связи
    sessions: Mapped[list["GameSession"]] = relationship(  # noqa: F821
        back_populates="user", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"
    
    def update_statistics(self) -> None:
        """Обновить статистику пользователя на основе завершённых сессий"""
        completed_sessions = [s for s in self.sessions if s.is_finished()]
        completed_rounds = []
        
        for session in completed_sessions:
            completed_rounds.extend([r for r in session.rounds if r.is_completed()])
        
        if not completed_sessions:
            return
        
        # Общая статистика
        self.games_played = len(completed_sessions)
        self.total_rounds = len(completed_rounds)
        
        # Счёт
        total_score = sum(s.total_score for s in completed_sessions)
        self.total_score = total_score
        self.average_score = total_score / self.games_played if self.games_played > 0 else 0
        
        # Лучший/худший счёт
        session_scores = [s.total_score for s in completed_sessions]
        if session_scores:
            self.best_score = max(session_scores)
            self.worst_score = min(session_scores)
        
        # Среднее расстояние
        if completed_rounds:
            total_distance = sum(
                float(r.distance_km) for r in completed_rounds 
                if r.distance_km is not None
            )
            self.average_distance = total_distance / len(completed_rounds)
        
        self.updated_at = datetime.utcnow()
    
    def add_experience(self, amount: int) -> None:
        """Добавить опыт"""
        self.experience += amount
        
        # Проверяем повышение уровня
        exp_for_next_level = self.get_experience_for_next_level()
        while self.experience >= exp_for_next_level:
            self.level += 1
            self.experience -= exp_for_next_level
            exp_for_next_level = self.get_experience_for_next_level()
        
        self.updated_at = datetime.utcnow()
    
    def get_experience_for_next_level(self) -> int:
        """Получить необходимое количество опыта для следующего уровня"""
        # Формула: 1000 * level^2
        return 1000 * (self.level ** 2)
    
    def get_experience_progress(self) -> float:
        """Получить прогресс до следующего уровня (0-1)"""
        exp_needed = self.get_experience_for_next_level()
        if exp_needed == 0:
            return 0.0
        return self.experience / exp_needed
    
    def update_elo_rating(self, opponent_rating: int, result: float) -> None:
        """Обновить рейтинг ELO"""
        # result: 1 - победа, 0.5 - ничья, 0 - поражение
        k_factor = 32  # Стандартный коэффициент K
        
        expected_score = 1 / (1 + 10 ** ((opponent_rating - self.elo_rating) / 400))
        self.elo_rating += int(k_factor * (result - expected_score))
        
        self.updated_at = datetime.utcnow()
    
    def get_rank(self) -> str:
        """Получить ранг пользователя"""
        if self.elo_rating >= 2400:
            return "Гроссмейстер"
        elif self.elo_rating >= 2200:
            return "Мастер"
        elif self.elo_rating >= 2000:
            return "Эксперт"
        elif self.elo_rating >= 1800:
            return "Продвинутый"
        elif self.elo_rating >= 1600:
            return "Средний"
        elif self.elo_rating >= 1400:
            return "Начинающий"
        else:
            return "Новичок"
    
    def update_activity(self) -> None:
        """Обновить время последней активности"""
        self.last_activity_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def to_dict(self, include_sessions: bool = False) -> dict:
        """Преобразовать пользователя в словарь"""
        result = {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name or self.username,
            "email": self.email,
            "total_score": self.total_score,
            "games_played": self.games_played,
            "games_won": self.games_won,
            "total_rounds": self.total_rounds,
            "average_score": self.average_score,
            "average_distance": self.average_distance,
            "best_score": self.best_score,
            "worst_score": self.worst_score,
            "elo_rating": self.elo_rating,
            "rank": self.get_rank(),
            "level": self.level,
            "experience": self.experience,
            "experience_progress": self.get_experience_progress(),
            "experience_for_next_level": self.get_experience_for_next_level(),
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "country": self.country,
            "timezone": self.timezone,
            "language": self.language,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "is_premium": self.is_premium,
            "email_verified": self.email_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None,
        }
        
        if include_sessions:
            result["sessions"] = [s.to_dict() for s in self.sessions]
        
        return result
