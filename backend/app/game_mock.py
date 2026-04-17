"""
Mock game implementation without database.
"""

import random
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/mock", tags=["mock"])


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


# In-memory storage for testing
sessions = {}
rounds = {}


@router.post("/sessions/start", response_model=SessionResponse)
async def start_game_session(request: StartRequest):
    """Start a new game session (mock version)."""
    session_id = str(uuid.uuid4())

    # Create mock round
    round_id = str(uuid.uuid4())

    # Generate random point in Russia
    target_lat = random.uniform(45.0, 70.0)  # Russia latitude range
    target_lon = random.uniform(30.0, 180.0)  # Russia longitude range

    round_obj = {
        "id": round_id,
        "session_id": session_id,
        "round_number": 1,
        "status": "active",
        "target_lat": target_lat,
        "target_lon": target_lon,
        "satellite_image_url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "created_at": datetime.now(timezone.utc),
    }

    rounds[round_id] = round_obj

    session = {
        "id": session_id,
        "mode": "standard",
        "status": "active",
        "rounds_total": request.rounds_total,
        "rounds_done": 0,
        "total_score": 0,
        "started_at": datetime.now(timezone.utc),
        "finished_at": None,
        "current_round_id": round_id,
    }

    sessions[session_id] = session

    return SessionResponse(
        id=session_id,
        mode="standard",
        status="active",
        rounds_total=request.rounds_total,
        rounds_done=0,
        total_score=0,
        started_at=session["started_at"].isoformat() + "Z",
        finished_at=None,
        current_round=RoundResponse(
            id=round_id,
            round_number=1,
            status="active",
            satellite_image_url=round_obj["satellite_image_url"],
            target_point=Point(lat=target_lat, lon=target_lon),
            created_at=round_obj["created_at"].isoformat() + "Z",
        ),
    )


@router.get("/rounds/{round_id}", response_model=RoundResponse)
async def get_round(round_id: str):
    """Get round information (mock version)."""
    if round_id not in rounds:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Round not found")

    round_obj = rounds[round_id]

    guess_point = None
    if "guess_lat" in round_obj:
        guess_point = Point(lat=round_obj["guess_lat"], lon=round_obj["guess_lon"])

    completed_at = None
    if "completed_at" in round_obj:
        completed_at = round_obj["completed_at"].isoformat() + "Z"

    return RoundResponse(
        id=round_obj["id"],
        round_number=round_obj["round_number"],
        status=round_obj["status"],
        satellite_image_url=round_obj["satellite_image_url"],
        target_point=Point(lat=round_obj["target_lat"], lon=round_obj["target_lon"]),
        guess_point=guess_point,
        distance_meters=round_obj.get("distance_meters"),
        score=round_obj.get("score"),
        created_at=round_obj["created_at"].isoformat() + "Z",
        completed_at=completed_at,
    )


@router.post("/rounds/{round_id}/guess", response_model=GuessResponse)
async def submit_guess(round_id: str, guess: GuessRequest):
    """Submit a guess for a round (mock version)."""
    if round_id not in rounds:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Round not found")

    round_obj = rounds[round_id]
    session_id = round_obj["session_id"]

    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    # Calculate distance (simplified)
    from math import atan2, cos, radians, sin, sqrt

    lat1 = radians(round_obj["target_lat"])
    lon1 = radians(round_obj["target_lon"])
    lat2 = radians(guess.lat)
    lon2 = radians(guess.lon)

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    radius = 6371000  # Earth radius in meters
    distance = radius * c

    # Calculate score
    max_score = 5000
    max_distance = 100000  # 100 km
    score = int(max_score * max(0, 1 - distance / max_distance))

    # Update round
    round_obj["guess_lat"] = guess.lat
    round_obj["guess_lon"] = guess.lon
    round_obj["distance_meters"] = distance
    round_obj["score"] = score
    round_obj["status"] = "completed"
    round_obj["completed_at"] = datetime.now(timezone.utc)

    # Update session
    session["rounds_done"] += 1
    session["total_score"] += score

    # Check if session is complete
    session_completed = False
    next_round = None

    if session["rounds_done"] >= session["rounds_total"]:
        session["status"] = "completed"
        session["finished_at"] = datetime.now(timezone.utc)
        session_completed = True
    else:
        # Create next round
        next_round_id = str(uuid.uuid4())
        next_target_lat = random.uniform(45.0, 70.0)
        next_target_lon = random.uniform(30.0, 180.0)

        next_round_obj = {
            "id": next_round_id,
            "session_id": session_id,
            "round_number": session["rounds_done"] + 1,
            "status": "active",
            "target_lat": next_target_lat,
            "target_lon": next_target_lon,
            "satellite_image_url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            "created_at": datetime.now(timezone.utc),
        }

        rounds[next_round_id] = next_round_obj
        session["current_round_id"] = next_round_id

        next_round = RoundResponse(
            id=next_round_id,
            round_number=next_round_obj["round_number"],
            status="active",
            satellite_image_url=next_round_obj["satellite_image_url"],
            target_point=Point(lat=next_target_lat, lon=next_target_lon),
            created_at=next_round_obj["created_at"].isoformat() + "Z",
        )

    return GuessResponse(
        round_id=round_id,
        distance_meters=distance,
        score=score,
        target_point=Point(lat=round_obj["target_lat"], lon=round_obj["target_lon"]),
        guess_point=Point(lat=guess.lat, lon=guess.lon),
        next_round=next_round,
        session_completed=session_completed,
    )
