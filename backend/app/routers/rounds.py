"""
Роутер для работы с игровыми раундами.
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.game_session import GameSession, SessionStatus
from app.models.round import Round
from app.models.user import User
from app.schemas.game import (
    RoundResponse,
    SubmitGuessRequest,
    GuessResponse,
    ZoneResponse,
    ErrorResponse,
)
from app.services.challenge_generator import ChallengeGenerator, GeometryUtils

router = APIRouter(prefix="/api/rounds", tags=["rounds"])
logger = logging.getLogger(__name__)


from app.auth_selector import get_current_user


@router.get(
    "/{round_id}",
    response_model=RoundResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Раунд не найден"},
    },
)
async def get_round(
    round_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить информацию о раунде.
    
    Возвращает информацию о раунде, включая космический снимок.
    Для завершённых раундов также возвращает результат.
    """
    try:
        # Получаем раунд и проверяем права доступа
        stmt = select(Round).join(GameSession).where(
            Round.id == round_id,
            GameSession.user_id == current_user.id
        )
        result = await db.execute(stmt)
        round_obj = result.scalar_one_or_none()
        
        if not round_obj:
            raise HTTPException(
                status_code=404,
                detail="Раунд не найден"
            )
        
        # Формируем ответ
        response = RoundResponse(
            id=round_obj.id,
            zone=ZoneResponse(
                id=round_obj.zone.id,
                name=round_obj.zone.name,
                description=round_obj.zone.description,
                difficulty=round_obj.zone.difficulty,
                category=round_obj.zone.category,
            ),
            satellite_image_url="",  # TODO: Получить URL снимка из satellite_provider
            view_extent_km=round_obj.view_extent_km,
            created_at=round_obj.created_at,
        )
        
        # Если раунд завершён, добавляем результат
        if round_obj.guess_point:
            from geoalchemy2.shape import to_shape
            guess_point = to_shape(round_obj.guess_point)
            response.guess_point = (guess_point.x, guess_point.y)
            response.distance_km = round_obj.distance_km
            response.score = round_obj.score
            response.guessed_at = round_obj.guessed_at
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting round: {e}")
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера"
        )


@router.post(
    "/{round_id}/guess",
    response_model=GuessResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Раунд уже завершён"},
        404: {"model": ErrorResponse, "description": "Раунд не найден"},
    },
)
async def submit_guess(
    round_id: int,
    request: SubmitGuessRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Отправить догадку для раунда.
    
    Принимает координаты выбранной точки, вычисляет расстояние
    до правильного ответа, начисляет очки и переходит к следующему раунду.
    """
    try:
        # Получаем раунд и проверяем права доступа
        stmt = select(Round).join(GameSession).where(
            Round.id == round_id,
            GameSession.user_id == current_user.id,
            GameSession.status == SessionStatus.ACTIVE
        )
        result = await db.execute(stmt)
        round_obj = result.scalar_one_or_none()
        
        if not round_obj:
            raise HTTPException(
                status_code=404,
                detail="Активный раунд не найден"
            )
        
        # Проверяем, что раунд ещё не завершён
        if round_obj.guess_point:
            raise HTTPException(
                status_code=400,
                detail="Раунд уже завершён"
            )
        
        # Получаем сессию
        session = round_obj.session
        
        # 1. Вычисляем расстояние между догадкой и правильным ответом
        from geoalchemy2.shape import to_shape
        target_point = to_shape(round_obj.target_point)
        distance_km = GeometryUtils.calculate_distance(
            point1_lng=request.longitude,
            point1_lat=request.latitude,
            point2_lng=target_point.x,
            point2_lat=target_point.y,
        )
        
        # 2. Вычисляем очки
        score = GeometryUtils.calculate_score(distance_km, max_distance_km=100)
        
        # 3. Обновляем раунд
        from geoalchemy2 import WKTElement
        
        update_stmt = update(Round).where(
            Round.id == round_id
        ).values(
            guess_point=WKTElement(f"POINT({request.longitude} {request.latitude})", srid=4326),
            distance_km=distance_km,
            score=score,
            guessed_at=datetime.utcnow()
        )
        await db.execute(update_stmt)
        
        # 4. Обновляем статистику сессии
        session.rounds_done += 1
        session.total_score += score
        
        # 5. Проверяем, завершена ли сессия
        is_session_finished = False
        next_round = None
        
        if session.rounds_done >= session.rounds_total:
            # Завершаем сессию
            session.status = SessionStatus.FINISHED
            session.finished_at = datetime.utcnow()
            is_session_finished = True
        else:
            # Генерируем следующий раунд
            generator = ChallengeGenerator(db)
            next_round = await generator.generate_round(
                session_id=session.id,
                zone_id=round_obj.zone_id,
                view_extent_km=round_obj.view_extent_km,
            )
            
            if not next_round:
                logger.error(f"Failed to generate next round for session {session.id}")
                # Если не удалось сгенерировать следующий раунд, завершаем сессию
                session.status = SessionStatus.FINISHED
                session.finished_at = datetime.utcnow()
                is_session_finished = True
        
        # 6. Обновляем общий счёт пользователя
        user_update_stmt = update(User).where(
            User.id == current_user.id
        ).values(
            total_score=User.total_score + score
        )
        await db.execute(user_update_stmt)
        
        await db.commit()
        
        # 7. Формируем ответ
        response = GuessResponse(
            round_id=round_obj.id,
            session_id=session.id,
            distance_km=distance_km,
            score=score,
            total_session_score=session.total_score,
            rounds_done=session.rounds_done,
            rounds_total=session.rounds_total,
            is_session_finished=is_session_finished,
        )
        
        # 8. Добавляем информацию о следующем раунде (если есть)
        if next_round and not is_session_finished:
            response.next_round = RoundResponse(
                id=next_round.id,
                zone=ZoneResponse(
                    id=next_round.zone.id,
                    name=next_round.zone.name,
                    description=next_round.zone.description,
                    difficulty=next_round.zone.difficulty,
                    category=next_round.zone.category,
                ),
                satellite_image_url="",  # TODO: Получить URL снимка
                view_extent_km=next_round.view_extent_km,
                created_at=next_round.created_at,
            )
        
        logger.info(
            f"Guess submitted for round {round_id}: "
            f"distance={distance_km:.2f}km, score={score}"
        )
        
        return response
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error submitting guess: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера при обработке догадки"
        )


@router.get(
    "/{round_id}/hint",
    responses={
        404: {"model": ErrorResponse, "description": "Раунд не найден"},
    },
)
async def get_hint(
    round_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Получить подсказку для раунда.
    
    Возвращает дополнительную информацию о местности
    (например, название страны, региона, или тип местности).
    """
    try:
        # Получаем раунд и проверяем права доступа
        stmt = select(Round).join(GameSession).where(
            Round.id == round_id,
            GameSession.user_id == current_user.id
        )
        result = await db.execute(stmt)
        round_obj = result.scalar_one_or_none()
        
        if not round_obj:
            raise HTTPException(
                status_code=404,
                detail="Раунд не найден"
            )
        
        # TODO: Реализовать получение подсказок
        # Например, через геокодирование или базу знаний о местности
        
        # Временная заглушка
        zone = round_obj.zone
        hint = {
            "zone_name": zone.name,
            "difficulty": zone.difficulty,
            "category": zone.category,
            "hint": f"Это местность в зоне '{zone.name}'. "
                   f"Сложность: {zone.difficulty}/5.",
        }
        
        return hint
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting hint: {e}")
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера"
        )