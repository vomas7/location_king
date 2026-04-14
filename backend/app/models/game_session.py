from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GameMode(StrEnum):
    SOLO = "solo"
    MULTIPLAYER = "multiplayer"


class SessionStatus(StrEnum):
    ACTIVE = "active"
    FINISHED = "finished"
    ABANDONED = "abandoned"


class GameSession(Base):
    __tablename__ = "game_sessions"

    # UUID генерируется на стороне PostgreSQL
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default=GameMode.SOLO
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SessionStatus.ACTIVE, index=True
    )

    rounds_total: Mapped[int] = mapped_column(SmallInteger, default=5)
    rounds_done: Mapped[int] = mapped_column(SmallInteger, default=0)
    total_score: Mapped[int] = mapped_column(Integer, default=0)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Связи
    user: Mapped["User"] = relationship(back_populates="sessions")  # noqa: F821
    rounds: Mapped[list["Round"]] = relationship(  # noqa: F821
        back_populates="session", lazy="select", order_by="Round.created_at"
    )

    def __repr__(self) -> str:
        return f"<GameSession id={self.id} user_id={self.user_id} status={self.status!r}>"
