"""Схемы обратной связи."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import FeedbackKind

#: Столько же символов принимает поле в интерфейсе. Ограничение не от
#: многословных: это защита базы от того, кто вставит туда мегабайт
MAX_MESSAGE_LENGTH = 2000


class FeedbackRequest(BaseModel):
    """Отзыв игрока."""

    kind: FeedbackKind
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)

    @field_validator("message")
    @classmethod
    def check_not_blank(cls, value: str) -> str:
        """Пробелы — это не сообщение, а промах по кнопке."""
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Напиши, что случилось")
        return cleaned


class FeedbackView(BaseModel):
    """Оставленный отзыв. Возвращается автору, чтобы было видно, что дошло."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: FeedbackKind
    message: str
    created_at: datetime
