"""
Select authentication method based on DEBUG mode.
"""

from fastapi import Depends
from typing import Union
from app.config import settings
from app.models.user import User

if settings.debug:
    from app.auth_debug import get_current_user_debug as get_current_user_impl
else:
    from app.auth import get_current_user as get_current_user_impl


async def get_current_user(*args, **kwargs) -> User:
    """Get current user (auto-selects debug or production auth)."""
    return await get_current_user_impl(*args, **kwargs)