from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Feedback(Base):
    """
    Что игрок написал о игре.

    Уходит вместе с учётной записью: политика обещает, что данные можно
    стереть, и отзыв — такие же его данные, как партии. Поэтому запись
    удаляется каскадом, а не остаётся сиротой с обезличенным автором.
    """

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    kind: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    # Читают отзыв всегда вместе с тем, кто его написал
    author: Mapped["User"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return f"<Feedback id={self.id} kind={self.kind!r}>"
