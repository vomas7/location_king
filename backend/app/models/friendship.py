from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import FriendshipStatus


class Friendship(Base):
    """
    Связь двух игроков: заявка и подтверждённая дружба.

    Одна строка на пару, а не две встречные: иначе пришлось бы держать их
    согласованными, а «дружба у одного есть, у другого нет» — это состояние,
    которого быть не должно. Кто кого позвал, видно по направлению строки.
    """

    __tablename__ = "friendships"
    __table_args__ = (UniqueConstraint("requester_id", "addressee_id", name="uq_friendship_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    requester_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    addressee_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=FriendshipStatus.PENDING,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    requester: Mapped["User"] = relationship(foreign_keys=[requester_id])  # noqa: F821
    addressee: Mapped["User"] = relationship(foreign_keys=[addressee_id])  # noqa: F821

    def __repr__(self) -> str:
        return f"<Friendship {self.requester_id}→{self.addressee_id} {self.status!r}>"
