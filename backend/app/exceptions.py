"""
Ошибки уровня приложения.

Сервисы бросают их, не зная про HTTP; обработчик в main.py превращает их в
ответы. Так бизнес-логика не тянет за собой FastAPI.

Сообщение берётся из `app/messages.py` и знает оба языка сразу: на каком
отвечать игроку, решает обработчик по заголовку запроса. Обычная строка тоже
принимается — тогда она одинакова на всех языках.
"""

from app.messages import Message


class AppError(Exception):
    """Базовая ошибка приложения с понятным пользователю сообщением."""

    status_code = 400

    def __init__(self, detail: str | Message):
        message = detail if isinstance(detail, Message) else Message(detail, detail)

        # В журнал и в текст исключения уходит русский: читать логи на двух
        # языках вперемешку невозможно
        super().__init__(message.ru)
        self.message = message
        self.detail = message.ru

    @property
    def headers(self) -> dict[str, str]:
        """Дополнительные заголовки ответа."""
        return {}


class ValidationError(AppError):
    """Данные не проходят правило, которое не выразить схемой запроса."""

    status_code = 400


class AuthError(AppError):
    """Не удалось подтвердить личность: неверные данные или токен."""

    status_code = 401


class ForbiddenError(AppError):
    """Личность подтверждена, но доступа к объекту нет."""

    status_code = 403


class NotFoundError(AppError):
    """Объект не найден."""

    status_code = 404


class ConflictError(AppError):
    """Действие противоречит текущему состоянию объекта."""

    status_code = 409


class UpstreamError(AppError):
    """Внешний сервис не ответил или ответил ошибкой."""

    status_code = 502


class TooManyRequestsError(AppError):
    """Запросов слишком много: сработало ограничение частоты."""

    status_code = 429

    def __init__(self, detail: str | Message, retry_after: int):
        super().__init__(detail)
        self.retry_after = retry_after

    @property
    def headers(self) -> dict[str, str]:
        return {"Retry-After": str(self.retry_after)}
