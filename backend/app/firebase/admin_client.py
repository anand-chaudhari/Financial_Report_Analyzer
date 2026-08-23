import os
from typing import Optional
import firebase_admin
from firebase_admin import credentials
from ..config import get_settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

_firebase_app: Optional[firebase_admin.App] = None


def get_firebase_app() -> Optional[firebase_admin.App]:
    """Initializes and returns the singleton Firebase Admin App instance."""
    global _firebase_app
    
    if _firebase_app is not None:
        return _firebase_app
        
    settings = get_settings()
    cred_path = settings.FIREBASE_CREDENTIALS_PATH
    
    try:
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            options = {}
            if settings.FIREBASE_STORAGE_BUCKET:
                options["storageBucket"] = settings.FIREBASE_STORAGE_BUCKET
            _firebase_app = firebase_admin.initialize_app(cred, options=options)
            logger.info("Firebase Admin SDK initialized successfully with serviceAccountKey.")
        else:
            logger.warning(
                f"Firebase credentials file not found at '{cred_path}'. "
                "Running in development/mock mode. Provide serviceAccountKey.json for live Firebase authentication."
            )
            # Check if default app exists
            if not firebase_admin._apps:
                # Mock or uninitialized state
                _firebase_app = None
            else:
                _firebase_app = firebase_admin.get_app()
    except Exception as e:
        logger.error(f"Error initializing Firebase Admin SDK: {str(e)}")
        _firebase_app = None
        
    return _firebase_app


def is_firebase_initialized() -> bool:
    """Checks if Firebase Admin is actively initialized with valid credentials."""
    return get_firebase_app() is not None
