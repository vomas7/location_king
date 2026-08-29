"""HTTP-слой обратной связи."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, limit_by_user
from app.models.user import User
from app.schemas.feedback import FeedbackRequest, FeedbackView
from app.services import feedback as feedback_service
from app.services.rate_limit import Limit

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


@router.post(
    "",
    response_model=FeedbackView,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_by_user(Limit.FEEDBACK))],
)
async def leave_feedback(
    payload: FeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FeedbackView:
    """Записать, что игрок думает об игре или что у него сломалось."""
    entry = await feedback_service.leave(db, user, payload.kind, payload.message)
    return FeedbackView.model_validate(entry)
