"""
Authentication module for Location King.
Handles JWT validation with Keycloak.
"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt.algorithms import RSAAlgorithm
import httpx
from typing import Optional

from app.config import settings
from app.models.user import User
from app.database import AsyncSession, get_db

security = HTTPBearer()

# Cache for JWKS
_jwks_cache = None
_jwks_cache_time = 0


async def get_jwks() -> dict:
    """Fetch JWKS from Keycloak."""
    global _jwks_cache, _jwks_cache_time
    import time
    
    # Cache for 5 minutes
    if _jwks_cache and time.time() - _jwks_cache_time < 300:
        return _jwks_cache
    
    jwks_url = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/certs"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            _jwks_cache = response.json()
            _jwks_cache_time = time.time()
            return _jwks_cache
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch JWKS: {str(e)}"
        )


def get_public_key(jwks: dict, kid: str) -> Optional[str]:
    """Get public key from JWKS by kid."""
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return RSAAlgorithm.from_jwk(key)
    return None


async def validate_token(token: str) -> dict:
    """Validate JWT token and return payload."""
    try:
        # Decode without verification to get kid
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing kid"
            )
        
        # Get JWKS and public key
        jwks = await get_jwks()
        public_key = get_public_key(jwks, kid)
        
        if not public_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: public key not found"
            )
        
        # Verify token
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience=settings.KEYCLOAK_CLIENT_ID,
            issuer=f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
        )
        
        return payload
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.
    
    For development/testing, returns a test user if no Keycloak URL is configured.
    """
    # Development mode - return test user
    if not settings.KEYCLOAK_URL or settings.KEYCLOAK_URL == "https://locationking.ru/auth":
        # TODO: Remove this after Keycloak is configured
        from sqlalchemy import select
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
                email_verified=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        return user
    
    # Production mode - validate JWT
    token = credentials.credentials
    payload = await validate_token(token)
    
    # Get or create user from database
    keycloak_id = payload.get("sub")
    email = payload.get("email")
    display_name = payload.get("preferred_username") or email.split("@")[0]
    
    from sqlalchemy import select
    from app.models.user import User as UserModel
    
    result = await db.execute(
        select(UserModel).where(UserModel.keycloak_id == keycloak_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Create new user
        user = UserModel(
            keycloak_id=keycloak_id,
            email=email,
            display_name=display_name,
            is_verified=True,
            email_verified=payload.get("email_verified", False)
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # Update existing user if needed
        update_needed = False
        if user.email != email:
            user.email = email
            update_needed = True
        if user.display_name != display_name:
            user.display_name = display_name
            update_needed = True
        
        if update_needed:
            await db.commit()
            await db.refresh(user)
    
    return user


# For backward compatibility during transition
async def get_current_user_deprecated() -> User:
    """
    Deprecated: Returns test user for development.
    Will be removed after auth is fully implemented.
    """
    from app.models.user import User as UserModel
    return UserModel(
        id=1,
        keycloak_id="test-user",
        email="test@example.com",
        display_name="Test User",
        is_verified=True,
        email_verified=True
    )