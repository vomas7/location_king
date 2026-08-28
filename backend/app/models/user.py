from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import Theme
from app.utils.elo import START_RATING


class User(Base):
    """Игрок."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))

    # Аватарка — два числа, а не файл: узор по ним рисует клиент. Подробности
    # и причина такого решения в app/utils/avatar.py
    avatar_shape: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    avatar_color: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)

    # По этому коду игрока добавляют в друзья. Не по имени: имена не
    # уникальны, а искать людей по чужому имени — способ найти не того
    friend_code: Mapped[str] = mapped_column(String(8), nullable=False, unique=True, index=True)

    # Оформление хранится у игрока, а не в браузере: тема должна пережить и
    # чистое хранилище, и другое устройство
    theme: Mapped[str] = mapped_column(String(10), nullable=False, default=Theme.DARK)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    # Статистика — пересчитывается сервисом после каждой завершённой сессии
    total_score: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    games_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_rounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    best_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_score: Mapped[float | None] = mapped_column(Float)
    average_distance: Mapped[float | None] = mapped_column(Float)

    # Рейтинг считается только по дуэлям: там соперники играют одну и ту же
    # серию раундов, и условия партии сокращаются. Из обычных партий вывести
    # его нельзя — они у всех разной сложности
    rating: Mapped[int] = mapped_column(Integer, nullable=False, default=START_RATING, index=True)
    duels_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # passive_deletes: партии и раунды удаляет сама база по внешнему ключу.
    # Без этого SQLAlchemy при удалении игрока полез бы читать все его партии,
    # чтобы обнулить ссылку, — и упёрся бы в NOT NULL.
    sessions: Mapped[list["GameSession"]] = relationship(  # noqa: F821
        back_populates="user",
        lazy="select",
        cascade="all, delete",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"

    @property
    def avatar(self) -> dict[str, int]:
        """Аватарка одним значением — в таком виде её ждут схемы ответов."""
        return {"shape": self.avatar_shape, "color": self.avatar_color}
