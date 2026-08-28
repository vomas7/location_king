"""Схемы аутентификации."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class RegisterRequest(BaseModel):
    """Регистрация по email и паролю."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    """Вход по email и паролю."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    """Обновление пары токенов."""

    refresh_token: str


class DeleteAccountRequest(BaseModel):
    """Удаление учётной записи. Пароль подтверждает, что это владелец."""

    password: str = Field(min_length=1, max_length=128)


class ProfileUpdateRequest(BaseModel):
    """
    Смена публичного лица игрока: имени, аватарки или того и другого.

    Все поля необязательные, но пустой запрос — это ошибка в клиенте, а не
    вежливое «ничего не делай»: он должен падать, а не молча проходить.
    """

    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    avatar_shape: int | None = Field(default=None, ge=0, le=99)
    avatar_color: int | None = Field(default=None, ge=0, le=99)

    @model_validator(mode="after")
    def check_something_changes(self) -> "ProfileUpdateRequest":
        if self.display_name is None and self.avatar_shape is None and self.avatar_color is None:
            raise ValueError("Нечего менять: укажи имя или аватарку")
        return self


class TokenPair(BaseModel):
    """Пара токенов и срок жизни access-токена в секундах."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AvatarView(BaseModel):
    """
    Аватарка: форма узора и цвет. Рисует её клиент.

    Приезжает в каждом ответе, где виден игрок, а не выводится клиентом из
    идентификатора: в таблице комнаты чужих идентификаторов нет и не будет.
    """

    shape: int
    color: int


class UserProfile(BaseModel):
    """Профиль игрока."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str | None
    email: EmailStr

    total_score: int
    games_played: int
    total_rounds: int
    best_score: int
    average_score: float | None
    average_distance: float | None

    #: Рейтинг дуэлей. У того, кто ещё не дуэлился, он стартовый — по нему
    #: подбирают первого соперника
    rating: int
    duels_played: int

    avatar: AvatarView

    created_at: datetime


class AuthResponse(BaseModel):
    """Ответ на регистрацию и вход."""

    user: UserProfile
    tokens: TokenPair
