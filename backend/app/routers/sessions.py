"""
Роутер для управления игровыми сессиями.
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.game_session import GameSession, GameMode, SessionStatus
from app.models.user import User
from app.schemas.game import (
    SessionResponse,
    StartSessionRequest,
    RoundResponse,
    ZoneResponse,
    ErrorResponse,
)
from app.services.challenge_generator import ChallengeGenerator

router = APIRouter(prefix="/api/sessions", tags=["sessions"])
logger = logging.getLogger(__name__)


# TODO: Реализовать аутентификацию через Keycloak
# Сейчас используем заглушку для тестирования
async def get_current_user() -> User:
    """
    Заглушка для аутентификации.
    В реальности должна проверять JWT токен от Keycloak.
    """
    # TODO: Заменить на реальную аутентификацию
    from app.models.user import User
    return User(id=1, keycloak_id="test-user", username="test_user", total_score=0)


@router.post(
    "/start",
    response_model=SessionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Некорректный запрос"},
        404: {"model": ErrorResponse, "description": "Зона не найдена"},
        500: {"model": ErrorResponse, "description": "Внутренняя ошибка сервера"},
    },
)
async def start_session(
    request: StartSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Начать новую игровую сессию.
    
    Создаёт новую сессию и генерирует первый раунд.
    """
    try:
        # Создаём генератор вызовов
        generator = ChallengeGenerator(db)
        
        # Определяем зону для игры
        zone_id = request.zone_id
        if not zone_id:
            # Выбираем случайную зону
            random_zone = await generator.get_random_zone(
                difficulty=request.difficulty,
                category=request.category,
            )
            if not random_zone:
                raise HTTPException(
                    status_code=404,
                    detail="Не найдено подходящих зон для игры"
                )
            zone_id = random_zone.id
        
        # Создаём игровую сессию
        session = GameSession(
            user_id=current_user.id,
            mode=GameMode.SOLO,
            status=SessionStatus.ACTIVE,
            rounds_total=request.rounds_total,
        )
        db.add(session)
        await db.flush()  # Получаем ID сессии
        
        # Генерируем первый раунд
        round_obj = await generator.generate_round(
            session_id=session.id,
            zone_id=zone_id,
            view_extent_km=5,  # По умолчанию 5км
        )
        
        if not round_obj:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Не удалось сгенерировать раунд"
            )
        
        await db.commit()
        
        # Формируем ответ
        return SessionResponse(
            id=session.id,
            mode=session.mode,
            status=session.status,
            rounds_total=session.rounds_total,
            rounds_done=session.rounds_done,
            total_score=session.total_score,
            started_at=session.started_at,
            finished_at=session.finished_at,
            current_round=RoundResponse(
                id=round_obj.id,
                zone=ZoneResponse(
                    id=round_obj.zone.id,
                    name=round_obj.zone.name,
                    description=round_obj.zone.description,
                    difficulty=round_obj.zone.difficulty,
                    category=round_obj.zone.category,
                ),
                satellite_image_url="",  # TODO: Получить URL снимка
                view_extent_km=round_obj.view_extent_km,
                created_at=round_obj.created_at,
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера при создании сессии"
        )


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Сессия не найдена"},
    },
)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить информацию об игровой сессии.
    
    Возвращает текущее состояние сессии и активный раунд.
    """
    try:
        # Проверяем, что сессия принадлежит текущему пользователю
        from sqlalchemy import select
        
        stmt = select(GameSession).where(
            GameSession.id == session_id,
            GameSession.user_id == current_user.id
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Сессия не найдена"
            )
        
        # Получаем активный раунд (последний не завершённый)
        from sqlalchemy import desc
        
        round_stmt = select(session.rounds).where(
            session.rounds.guess_point.is_(None)
        ).order_by(desc(session.rounds.created_at)).limit(1)
        
        round_result = await db.execute(round_stmt)
        current_round = round_result.scalar_one_or_none()
        
        # Формируем ответ
        response = SessionResponse(
            id=session.id,
            mode=session.mode,
            status=session.status,
            rounds_total=session.rounds_total,
            rounds_done=session.rounds_done,
            total_score=session.total_score,
            started_at=session.started_at,
            finished_at=session.finished_at,
        )
        
        if current_round:
            response.current_round = RoundResponse(
                id=current_round.id,
                zone=ZoneResponse(
                    id=current_round.zone.id,
                    name=current_round.zone.name,
                    description=current_round.zone.description,
                    difficulty=current_round.zone.difficulty,
                    category=current_round.zone.category,
                ),
                satellite_image_url="",  # TODO: Получить URL снимка
                view_extent_km=current_round.view_extent_km,
                created_at=current_round.created_at,
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session: {e}")
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера"
        )


@router.get(
    "/{session_id}/history",
    response_model=list[RoundResponse],
    responses={
        404: {"model": ErrorResponse, "description": "Сессия не найдена"},
    },
)
async def get_session_history(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить историю раундов сессии.
    
    Возвращает все завершённые раунды сессии.
    """
    try:
        # Проверяем, что сессия принадлежит текущему пользователю
        from sqlalchemy import select
        
        stmt = select(GameSession).where(
            GameSession.id == session_id,
            GameSession.user_id == current_user.id
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Сессия не найдена"
            )
        
        # Получаем завершённые раунды (с догадками)
        rounds = []
        for round_obj in session.rounds:
            if round_obj.guess_point:  # Только завершённые раунды
                rounds.append(RoundResponse(
                    id=round_obj.id,
                    zone=ZoneResponse(
                        id=round_obj.zone.id,
                        name=round_obj.zone.name,
                        description=round_obj.zone.description,
                        difficulty=round_obj.zone.difficulty,
                        category=round_obj.zone.category,
                    ),
                    satellite_image_url="",  # TODO: Получить URL снимка
                    view_extent_km=round_obj.view_extent_km,
                    created_at=round_obj.created_at,
                    guess_point=(round_obj.guess_point.x, round_obj.guess_point.y),
                    distance_km=round_obj.distance_km,
                    score=round_obj.score,
                    guessed_at=round_obj.guessed_at,
                ))
        
        return rounds
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session history: {e}")
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера"
        )


@router.post(
    "/{session_id}/finish",
    response_model=SessionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Сессия не найдена"},
    },
)
async def finish_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Завершить игровую сессию досрочно.
    
    Устанавливает статус сессии как FINISHED.
    """
    try:
        from sqlalchemy import select, update
        from datetime import datetime
        
        # Проверяем, что сессия принадлежит текущему пользователю
        stmt = select(GameSession).where(
            GameSession.id == session_id,
            GameSession.user_id == current_user.id,
            GameSession.status == SessionStatus.ACTIVE
        )
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Активная сессия не найдена"
            )
        
        # Обновляем статус сессии
        update_stmt = update(GameSession).where(
            GameSession.id == session_id
        ).values(
            status=SessionStatus.FINISHED,
            finished_at=datetime.utcnow()
        )
        await db.execute(update_stmt)
        await db.commit()
        
        # Получаем обновлённую сессию
        result = await db.execute(stmt)
        updated_session = result.scalar_one_or_none()
        
        return SessionResponse(
            id=updated_session.id,
            mode=updated_session.mode,
            status=updated_session.status,
            rounds_total=updated_session.rounds_total,
            rounds_done=updated_session.rounds_done,
            total_score=updated_session.total_score,
            started_at=updated_session.started_at,
            finished_at=updated_session.finished_at,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finishing session: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера"
        )