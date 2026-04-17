"""
Simplified authentication module for Location King.
Always returns test user for now.
"""

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User


async def get_current_user(
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current authenticated user.

    For now, always returns a test user until auth is fully implemented.
    """
    # Get or create test user
    from app.models.user import User as UserModel

    result = await db.execute(select(UserModel).where(UserModel.id == 1))
    user = result.scalar_one_or_none()

    if not user:
        # Create test user if doesn't exist
        user = UserModel(
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
