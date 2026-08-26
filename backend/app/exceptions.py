"""
Ошибки уровня приложения.

Сервисы бросают их, не зная про HTTP; обработчик в main.py превращает их в
ответы. Так бизнес-логика не тянет за собой FastAPI.
"""


class AppError(Exception):
    """Базовая ошибка приложения с понятным пользователю сообщением."""

    status_code = 400

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


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
