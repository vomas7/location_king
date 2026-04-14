"""
Test router for debugging without authentication.
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
    StartSessionRequest,
    ZoneResponse,
    ErrorResponse,
)
from app.schemas.test import TestSessionResponse, TestRoundResponse
from app.services.challenge_generator import ChallengeGenerator

router = APIRouter(prefix="/api/test", tags=["test"])
logger = logging.getLogger(__name__)


@router.post("/session/start", response_model=TestSessionResponse)
async def start_test_session(
    request: StartSessionRequest,
    db: AsyncSession = Depends(get_db)
):
    """Start a test session without authentication."""
    try:
        # Get or create test user
        from sqlalchemy.future import select
        import uuid
        
        result = await db.execute(
            select(User).where(User.email == "test@example.com")
        )
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                email="test@example.com",
                display_name="Test Player",
                keycloak_id=str(uuid.uuid4()),
                is_verified=True,
                email_verified=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        # Create game session
        session = GameSession(
            user_id=user.id,
            rounds_total=request.rounds_total or 5,
            rounds_done=0,
            total_score=0,
            status=SessionStatus.ACTIVE.value,
            mode=GameMode.SOLO.value,
            time_control=None,

        )
        
        db.add(session)
        await db.commit()
        await db.refresh(session)
        
        # Generate first round
        generator = ChallengeGenerator(db)
        
        # If zone_id not provided, get random zone
        zone_id = request.zone_id
        if not zone_id:
            from sqlalchemy.future import select
            from app.models.location_zone import LocationZone
            import random
            
            result = await db.execute(
                select(LocationZone.id).where(LocationZone.is_active == True)
            )
            zone_ids = result.scalars().all()
            if zone_ids:
                zone_id = random.choice(zone_ids)
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No active zones found"
                )
        
        round_obj = await generator.generate_round(
            session_id=session.id,
            zone_id=zone_id,
            view_extent_km=request.view_extent_km or 5
        )
        
        await db.commit()
        await db.refresh(round_obj)
        await db.refresh(session)
        
        # Prepare response
        from geoalchemy2.shape import to_shape
        
        if round_obj.target_point:
            # Извлекаем координаты из геометрии GeoAlchemy2
            shape = to_shape(round_obj.target_point)
            target_coords = [shape.x, shape.y]
        else:
            target_coords = [0, 0]
        
        round_response = TestRoundResponse(
            id=round_obj.id,
            session_id=round_obj.session_id,
            target_point={"type": "Point", "coordinates": target_coords},
            status=round_obj.status,
            max_score=round_obj.max_score,
            time_limit_seconds=round_obj.time_limit_seconds,
            started_at=round_obj.started_at,
            completed_at=round_obj.completed_at
        )
        
        
        return TestSessionResponse(
            id=session.id,
            user_id=session.user_id,
            rounds_total=session.rounds_total,
            rounds_done=session.rounds_done,
            total_score=session.total_score,
            status=session.status,
            game_mode=session.mode,
            time_control=session.time_control,
            view_extent_km=request.view_extent_km or 5,
            current_round=round_response
        )
        
    except Exception as e:
        logger.error(f"Error creating test session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/zones", response_model=list[ZoneResponse])
async def get_test_zones(db: AsyncSession = Depends(get_db)):
    """Get zones for testing."""
    from sqlalchemy.future import select
    from app.models.location_zone import LocationZone
    
    result = await db.execute(select(LocationZone))
    zones = result.scalars().all()
    
    return [
        ZoneResponse(
            id=zone.id,
            name=zone.name,
            description=zone.description,
            difficulty=zone.difficulty,
            category=zone.category,
            area_sq_km=zone.area_sq_km,
            country=zone.country,
            region=zone.region,
            is_featured=zone.is_featured,
            is_premium=zone.is_premium,
            created_at=zone.created_at,
            updated_at=zone.updated_at
        )
        for zone in zones
    ]