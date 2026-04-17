"""
Minimal test endpoint to debug 422 error.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/debug", tags=["debug"])


class TestRequest(BaseModel):
    rounds_total: int = 5
    view_extent_km: int = 5
    difficulty: int | None = 3


class TestResponse(BaseModel):
    id: str
    message: str
    rounds_total: int
    view_extent_km: int
    difficulty: int


@router.post("/start", response_model=TestResponse)
async def debug_start(request: TestRequest):
    """Minimal test endpoint with no dependencies."""
    return TestResponse(
        id="debug-session-123",
        message="Debug endpoint works!",
        rounds_total=request.rounds_total,
        view_extent_km=request.view_extent_km,
        difficulty=request.difficulty or 3,
    )
