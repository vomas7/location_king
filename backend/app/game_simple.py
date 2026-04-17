"""
Simple game implementation to replace broken routers.
"""

import random
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.game_session import GameMode, GameSession, SessionStatus
from app.models.location_zone import LocationZone
from app.models.round import Round, RoundStatus
from app.models.user import User

router = APIRouter(prefix="/api/game", tags=["game"])


class StartRequest(BaseModel):
    rounds_total: int = Field(5, ge=1, le=20)
    view_extent_km: int = Field(5, ge=1, le=50)
    difficulty: int | None = Field(None, ge=1, le=5)
    zone_id: int | None = None
    category: str | None = None


class Point(BaseModel):
    lat: float
    lon: float


class RoundResponse(BaseModel):
    id: str
    round_number: int
    status: str
    satellite_image_url: str
    target_point: Point
    guess_point: Point | None = None
    distance_meters: float | None = None
    score: int | None = None
    created_at: str
    completed_at: str | None = None


class SessionResponse(BaseModel):
    id: str
    mode: str
    status: str
    rounds_total: int
    rounds_done: int
    total_score: int
    started_at: str
    finished_at: str | None
    current_round: RoundResponse | None


class GuessRequest(BaseModel):
    lat: float
    lon: float


class GuessResponse(BaseModel):
    round_id: str
    distance_meters: float
    score: int
    target_point: Point
    guess_point: Point
    next_round: RoundResponse | None = None
    session_completed: bool = False


# Simple user dependency
async def get_current_user_simple(
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get or create test user."""
    result = await db.execute(select(User).where(User.id == 1))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=1,
            keycloak_id="test-user",
            email="test@example.com",
            display_name="Test User",
            is_verified=True,
            email_verified=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


@router.post("/sessions/start", response_model=SessionResponse)
async def start_game_session(
    request: StartRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_simple),
):
    """Start a new game session."""
    # Create session
    session = GameSession(
        user_id=current_user.id,
        mode=GameMode.STANDARD,
        status=SessionStatus.ACTIVE,
        rounds_total=request.rounds_total,
        rounds_done=0,
        total_score=0,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Get a random zone or use specified one
    zone = None
    if request.zone_id:
        result = await db.execute(select(LocationZone).where(LocationZone.id == request.zone_id))
        zone = result.scalar_one_or_none()

    if not zone:
        # Get random zone
        query = select(LocationZone)
        if request.difficulty:
            query = query.where(LocationZone.difficulty == request.difficulty)
        if request.category:
            query = query.where(LocationZone.category == request.category)

        result = await db.execute(query)
        zones = result.scalars().all()
        if zones:
            zone = random.choice(zones)

    if not zone:
        # Create a mock zone if none exists
        zone = LocationZone(
            name="Test Zone",
            bounds=[30.0, 50.0, 40.0, 60.0],  # Kyiv area
            difficulty=request.difficulty or 3,
            category=request.category or "test",
        )
        db.add(zone)
        await db.commit()
        await db.refresh(zone)

    # Create first round
    round_obj = await create_round(db, session.id, zone, 1, request.view_extent_km)

    # Prepare response
    return SessionResponse(
        id=str(session.id),
        mode=session.mode.value,
        status=session.status.value,
        rounds_total=session.rounds_total,
        rounds_done=session.rounds_done,
        total_score=session.total_score,
        started_at=session.created_at.isoformat() + "Z",
        finished_at=session.finished_at.isoformat() + "Z" if session.finished_at else None,
        current_round=RoundResponse(
            id=str(round_obj.id),
            round_number=round_obj.round_number,
            status=round_obj.status.value,
            satellite_image_url=round_obj.satellite_image_url
            or "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            target_point=Point(
                lat=round_obj.target_lat,
                lon=round_obj.target_lon,
            ),
            created_at=round_obj.created_at.isoformat() + "Z",
        ),
    )


async def create_round(
    db: AsyncSession,
    session_id: uuid.UUID,
    zone: LocationZone,
    round_number: int,
    view_extent_km: int,
) -> Round:
    """Create a new round."""
    # Generate random point within zone bounds
    bounds = zone.bounds
    min_lon, min_lat, max_lon, max_lat = bounds

    target_lon = random.uniform(min_lon, max_lon)
    target_lat = random.uniform(min_lat, max_lat)

    # Create satellite image URL (mock for now)
    satellite_url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"

    round_obj = Round(
        session_id=session_id,
        round_number=round_number,
        zone_id=zone.id,
        target_lat=target_lat,
        target_lon=target_lon,
        view_extent_km=view_extent_km,
        satellite_image_url=satellite_url,
        status=RoundStatus.ACTIVE,
    )

    db.add(round_obj)
    await db.commit()
    await db.refresh(round_obj)

    return round_obj


@router.post("/rounds/{round_id}/guess", response_model=GuessResponse)
async def submit_guess(
    round_id: str,
    guess: GuessRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_simple),
):
    """Submit a guess for a round."""
    # Get round
    result = await db.execute(
        select(Round).where(Round.id == uuid.UUID(round_id)),
    )
    round_obj = result.scalar_one_or_none()

    if not round_obj:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Round not found")

    # Get session
    result = await db.execute(
        select(GameSession).where(GameSession.id == round_obj.session_id),
    )
    session = result.scalar_one_or_none()

    # Calculate distance (simplified)
    from math import atan2, cos, radians, sin, sqrt

    lat1 = radians(round_obj.target_lat)
    lon1 = radians(round_obj.target_lon)
    lat2 = radians(guess.lat)
    lon2 = radians(guess.lon)

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    R = 6371000  # Earth radius in meters
    distance = R * c

    # Calculate score (simplified)
    max_score = 5000
    max_distance = 100000  # 100 km
    score = int(max_score * max(0, 1 - distance / max_distance))

    # Update round
    round_obj.guess_lat = guess.lat
    round_obj.guess_lon = guess.lon
    round_obj.distance_meters = distance
    round_obj.score = score
    round_obj.status = RoundStatus.COMPLETED
    round_obj.completed_at = datetime.utcnow()

    # Update session
    session.rounds_done += 1
    session.total_score += score

    # Check if session is complete
    session_completed = False
    next_round = None

    if session.rounds_done >= session.rounds_total:
        session.status = SessionStatus.COMPLETED
        session.finished_at = datetime.utcnow()
        session_completed = True
    else:
        # Create next round
        # Get zone
        result = await db.execute(select(LocationZone).where(LocationZone.id == round_obj.zone_id))
        zone = result.scalar_one()

        next_round_obj = await create_round(
            db,
            session.id,
            zone,
            session.rounds_done + 1,
            round_obj.view_extent_km,
        )

        next_round = RoundResponse(
            id=str(next_round_obj.id),
            round_number=next_round_obj.round_number,
            status=next_round_obj.status.value,
            satellite_image_url=next_round_obj.satellite_image_url,
            target_point=Point(
                lat=next_round_obj.target_lat,
                lon=next_round_obj.target_lon,
            ),
            created_at=next_round_obj.created_at.isoformat() + "Z",
        )

    await db.commit()

    return GuessResponse(
        round_id=str(round_obj.id),
        distance_meters=distance,
        score=score,
        target_point=Point(lat=round_obj.target_lat, lon=round_obj.target_lon),
        guess_point=Point(lat=guess.lat, lon=guess.lon),
        next_round=next_round,
        session_completed=session_completed,
    )
