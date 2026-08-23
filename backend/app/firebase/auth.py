from typing import Dict, Any, Optional
from firebase_admin import auth
from .admin_client import is_firebase_initialized, get_firebase_app
from ..config import get_settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


def verify_firebase_token(id_token: str) -> Optional[Dict[str, Any]]:
    """
    Verifies Firebase JWT token. In dev mode without credentials, supports dev mock token.
    """
    settings = get_settings()
    
    if not is_firebase_initialized():
        if settings.ENVIRONMENT == "development":
            # Allow development bypass token for testing without credentials
            logger.debug("Firebase uninitialized; using development mock auth check.")
            return {
                "uid": "dev_user_123",
                "email": "developer@financialanalyzer.local",
                "name": "Dev User"
            }
        return None

    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        logger.warning(f"Firebase token verification failed: {str(e)}")
        return None
