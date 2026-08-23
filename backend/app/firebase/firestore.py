from typing import Optional, Any
from firebase_admin import firestore
from .admin_client import is_firebase_initialized, get_firebase_app
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

_firestore_db = None


def get_firestore_client() -> Optional[Any]:
    """Returns Cloud Firestore client if Firebase Admin is initialized."""
    global _firestore_db
    
    if _firestore_db is not None:
        return _firestore_db
        
    app = get_firebase_app()
    if app:
        try:
            _firestore_db = firestore.client(app=app)
            return _firestore_db
        except Exception as e:
            logger.error(f"Failed to create Firestore client: {str(e)}")
            return None
    return None
