from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """Игрок."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    # Статистика — пересчитывается сервисом после каждой завершённой сессии
    total_score: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    games_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_rounds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    best_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_score: Mapped[float | None] = mapped_column(Float)
    average_distance: Mapped[float | None] = mapped_column(Float)

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
