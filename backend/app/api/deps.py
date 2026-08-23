from typing import Dict, Any, Optional
from fastapi import Depends, HTTPException, status, Header
from ..firebase.auth import verify_firebase_token
from ..config import get_settings, Settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


async def get_current_user(
    authorization: Optional[str] = Header(None),
    settings: Settings = Depends(get_settings)
) -> Dict[str, Any]:
    """
    FastAPI dependency to extract and verify Firebase Bearer token.
    Returns user payload dictionary (e.g., {'uid': '...', 'email': '...'}).
    """
    if not authorization:
        if settings.ENVIRONMENT == "development":
            # Permissive fallback for local testing without frontend auth
            return {
                "uid": "dev_user_123",
                "email": "dev@financialanalyzer.local",
                "name": "Local Developer"
            }
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    token = parts[1]
    user = verify_firebase_token(token)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return user


async def get_optional_user(
    authorization: Optional[str] = Header(None)
) -> Optional[Dict[str, Any]]:
    """Optional user dependency for public or semi-protected routes."""
    if not authorization:
        return None
    try:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return verify_firebase_token(parts[1])
    except Exception:
        pass
    return None
