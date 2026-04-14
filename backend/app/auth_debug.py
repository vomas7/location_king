"""
Debug authentication for testing.
When DEBUG=True, uses a test user instead of Keycloak.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.config import settings
from app.models.user import User
from app.database import AsyncSession, get_db
from sqlalchemy.future import select
import uuid

security = HTTPBearer()


async def get_current_user_debug(
    credentials: Optional[HTTPAuthorizationCredentials] = None,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user for debug mode."""
    if not settings.debug:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Debug mode is disabled"
        )
    
    # In debug mode, we accept any token or no token
    # Use test user if exists, otherwise create one
    
    # Look for test user
    result = await db.execute(
        select(User).where(User.email == "test@example.com")
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Create test user
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
    
    return user