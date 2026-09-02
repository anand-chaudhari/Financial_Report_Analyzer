from typing import Dict, Any, Optional
from firebase_admin import auth
from .admin_client import is_firebase_initialized, get_firebase_app
from ..config import get_settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


def verify_firebase_token(id_token: str) -> Optional[Dict[str, Any]]:
    """
    Verifies Firebase JWT token.
    - In development mode with no credentials: returns a mock user for local testing.
    - In production: verifies against Firebase Admin SDK; returns None on failure.
    """
    settings = get_settings()

    if not is_firebase_initialized():
        if settings.ENVIRONMENT == "development":
            # Allow dev bypass token for testing without credentials
            logger.debug("Firebase uninitialized; using development mock auth.")
            return {
                "uid": "dev_user_123",
                "email": "developer@financialanalyzer.local",
                "name": "Dev User"
            }
        # Production with no Firebase credentials — log clearly so the issue is obvious
        logger.error(
            "Firebase Admin SDK is NOT initialized in production. "
            "Set FIREBASE_SERVICE_ACCOUNT_JSON environment variable on Render. "
            "All authenticated requests will be rejected until this is fixed."
        )
        return None

    try:
        # Ensure we use the initialized app explicitly
        app = get_firebase_app()
        decoded_token = auth.verify_id_token(id_token, app=app)
        return decoded_token
    except auth.ExpiredIdTokenError:
        logger.warning("Firebase token verification failed: Token has expired.")
        return None
    except auth.InvalidIdTokenError as e:
        logger.warning(f"Firebase token verification failed: Invalid token — {str(e)}")
        return None
    except Exception as e:
        logger.warning(f"Firebase token verification failed: {str(e)}")
        return None
