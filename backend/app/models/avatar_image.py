from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, LargeBinary, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AvatarImage(Base):
    """
    Загруженная игроком аватарка.

    Отдельной таблицей, а не колонкой в users: картинка весит килобайты, а
    профиль читается на каждый запрос и в каждой строке таблицы лидеров.
    Лежит в базе, а не файлом на диске, — тогда её забирает тот же
    pg_dump, что и всё остальное, и удаление учётной записи уносит её
    каскадом, ничего не забыв на диске.
    """

    __tablename__ = "avatar_images"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    #: Готовый к отдаче WebP: квадрат, приведённый к одному размеру
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
