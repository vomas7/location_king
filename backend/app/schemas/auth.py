"""Схемы аутентификации."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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


class TokenPair(BaseModel):
    """Пара токенов и срок жизни access-токена в секундах."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


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

    created_at: datetime


class AuthResponse(BaseModel):
    """Ответ на регистрацию и вход."""

    user: UserProfile
    tokens: TokenPair
