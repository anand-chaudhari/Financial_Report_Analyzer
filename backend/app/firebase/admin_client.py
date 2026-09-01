import os
import json
import base64
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

    # Render Secret Files fallback: if user mounted serviceAccountKey.json as a Secret File
    RENDER_SECRET_PATH = "/etc/secrets/serviceAccountKey.json"
    if not os.path.exists(cred_path) and os.path.exists(RENDER_SECRET_PATH):
        cred_path = RENDER_SECRET_PATH

    # Priority 1: Environment variable containing raw JSON string (most common for Render)
    service_account_json_env = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON") or settings.FIREBASE_SERVICE_ACCOUNT_JSON
    # Priority 2: Environment variable containing Base64-encoded JSON string
    service_account_b64_env = os.getenv("FIREBASE_CREDENTIALS_BASE64") or settings.FIREBASE_CREDENTIALS_BASE64

    cred = None
    init_source = None

    try:
        if service_account_json_env and service_account_json_env.strip():
            logger.info("Parsing Firebase credentials from FIREBASE_SERVICE_ACCOUNT_JSON environment variable...")
            raw_json = service_account_json_env.strip()
            # Safely parse the JSON, then fix private_key newlines that cloud env vars often escape
            service_account_dict = json.loads(raw_json)
            if "private_key" in service_account_dict:
                # Unescape literal \n sequences that Render/GCP inject into multi-line values
                service_account_dict["private_key"] = service_account_dict["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(service_account_dict)
            init_source = "FIREBASE_SERVICE_ACCOUNT_JSON env var"
        elif service_account_b64_env and service_account_b64_env.strip():
            logger.info("Parsing Firebase credentials from FIREBASE_CREDENTIALS_BASE64 environment variable...")
            decoded_json = base64.b64decode(service_account_b64_env.strip()).decode("utf-8")
            service_account_dict = json.loads(decoded_json)
            if "private_key" in service_account_dict:
                service_account_dict["private_key"] = service_account_dict["private_key"].replace("\\n", "\n")
            cred = credentials.Certificate(service_account_dict)
            init_source = "FIREBASE_CREDENTIALS_BASE64 env var"
        elif os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            init_source = f"local file '{cred_path}'"

        if cred is not None:
            options = {}
            if settings.FIREBASE_STORAGE_BUCKET:
                options["storageBucket"] = settings.FIREBASE_STORAGE_BUCKET
            _firebase_app = firebase_admin.initialize_app(cred, options=options)
            logger.info(f"Firebase Admin SDK initialized successfully via {init_source}.")
        else:
            logger.warning(
                f"No Firebase credentials found in env vars, Render Secret Files, or local file '{cred_path}'. "
                "Running in development/mock mode. Set FIREBASE_SERVICE_ACCOUNT_JSON env var on Render, "
                "mount serviceAccountKey.json as a Render Secret File at /etc/secrets/serviceAccountKey.json, "
                "or place serviceAccountKey.json locally for development."
            )
            # Check if default app exists
            if not firebase_admin._apps:
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
