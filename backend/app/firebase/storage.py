from typing import Optional, Any
from firebase_admin import storage
from .admin_client import is_firebase_initialized, get_firebase_app
from ..config import get_settings
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


def get_storage_bucket() -> Optional[Any]:
    """Returns Firebase Storage bucket reference."""
    app = get_firebase_app()
    if not app:
        return None
        
    settings = get_settings()
    try:
        bucket_name = settings.FIREBASE_STORAGE_BUCKET or None
        bucket = storage.bucket(name=bucket_name, app=app)
        return bucket
    except Exception as e:
        logger.error(f"Failed to access Firebase Storage bucket: {str(e)}")
        return None
