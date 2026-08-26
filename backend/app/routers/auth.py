"""HTTP-слой аутентификации."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserProfile,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _tokens_for(user: User) -> TokenPair:
    return TokenPair(
        access_token=auth_service.create_token(user.id, "access"),
        refresh_token=auth_service.create_token(user.id, "refresh"),
        expires_in=settings.access_token_ttl_minutes * 60,
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    """Зарегистрировать пользователя и сразу выдать токены."""
    user = await auth_service.register(db, payload.email, payload.password, payload.display_name)
    return AuthResponse(user=UserProfile.model_validate(user), tokens=_tokens_for(user))


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> AuthResponse:
    """Войти по email и паролю."""
    user = await auth_service.authenticate(db, payload.email, payload.password)
    return AuthResponse(user=UserProfile.model_validate(user), tokens=_tokens_for(user))


@router.post("/guest", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def guest(db: AsyncSession = Depends(get_db)) -> AuthResponse:
    """Начать играть без регистрации."""
    user = await auth_service.create_guest(db)
    return AuthResponse(user=UserProfile.model_validate(user), tokens=_tokens_for(user))


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenPair:
    """Обменять refresh-токен на новую пару."""
    user_id = auth_service.decode_token(payload.refresh_token, "refresh")
    user = await auth_service.get_active_user(db, user_id)
    return _tokens_for(user)


@router.get("/me", response_model=UserProfile)
async def me(user: User = Depends(get_current_user)) -> UserProfile:
    """Профиль текущего игрока."""
    return UserProfile.model_validate(user)
