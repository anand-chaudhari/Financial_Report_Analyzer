import os
import json
import threading
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List
from ..firebase.firestore import get_firestore_client
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

def _get_cache_dir() -> str:
    base = os.getcwd()
    if os.path.basename(base) == "backend":
        cdir = os.path.join(base, "cache")
    else:
        cdir = os.path.join(base, "backend", "cache")
    os.makedirs(cdir, exist_ok=True)
    return cdir

CACHE_DIR = _get_cache_dir()

# Global in-memory cache fallback
_memory_cache: Dict[str, Dict[str, Any]] = {}
# Lock manager to prevent duplicate in-flight simultaneous generation requests
_in_flight_locks: Dict[str, threading.Lock] = {}
_global_lock = threading.Lock()


def safe_print(msg: str):
    """Safely prints log messages to console avoiding Windows cp1252 UnicodeEncodeError."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))


class AICacheService:
    """
    Centralized Persistent Result Caching & State Management Service for FinSight AI.
    Features:
    - Stable key generation from document/filing IDs, section type, and parameters.
    - Dual persistence in Firestore ('ai_analysis_cache') + Local Disk Storage + Memory.
    - Status tracking: 'pending', 'completed', 'failed'.
    - In-flight request deduplication/locking to prevent simultaneous duplicate LLM requests.
    - Required console debug logging: CACHE HIT, CACHE MISS, CACHE SAVED, INPUT CHANGED.
    """

    def __init__(self):
        self.firestore_db = get_firestore_client()

    @staticmethod
    def build_cache_key(
        section: str,
        user_id: str,
        document_id: Optional[str] = None,
        document_b_id: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Creates a stable, deterministic input version key based on section, user, document IDs, and options.
        """
        user_clean = user_id or "default_user"
        parts = [section, user_clean]
        if document_id:
            parts.append(document_id)
        if document_b_id:
            parts.append(document_b_id)
        if extra_params:
            sorted_params = json.dumps(extra_params, sort_keys=True)
            param_hash = hashlib.md5(sorted_params.encode("utf-8")).hexdigest()[:8]
            parts.append(param_hash)

        raw_key = ":".join(parts)
        # Sanitize for valid Firestore doc ID & filename
        sanitized_key = re_sanitize_key(raw_key)
        return sanitized_key

    def get_lock_for_key(self, cache_key: str) -> threading.Lock:
        """Retrieves or creates a thread-safe lock for in-flight request deduplication."""
        with _global_lock:
            if cache_key not in _in_flight_locks:
                _in_flight_locks[cache_key] = threading.Lock()
            return _in_flight_locks[cache_key]

    def get_cached_result(
        self,
        cache_key: str,
        force_refresh: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Checks if a completed result exists for the exact cache_key.
        Returns the data dictionary if CACHE HIT, else None if CACHE MISS.
        """
        if force_refresh:
            safe_print(f"INPUT CHANGED -> regenerating [key: '{cache_key}']")
            logger.info(f"INPUT CHANGED -> regenerating [key: '{cache_key}']")
            return None

        # 1. Check In-Memory Cache
        if cache_key in _memory_cache:
            item = _memory_cache[cache_key]
            if item.get("status") == "completed" and item.get("data"):
                safe_print(f"CACHE HIT -> no AI request [key: '{cache_key}']")
                logger.info(f"CACHE HIT -> no AI request [key: '{cache_key}']")
                return item["data"]

        # 2. Check Local Disk Cache File
        disk_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
        if os.path.exists(disk_file):
            try:
                with open(disk_file, "r", encoding="utf-8") as f:
                    item = json.load(f)
                if item.get("status") == "completed" and item.get("data"):
                    _memory_cache[cache_key] = item
                    safe_print(f"CACHE HIT -> no AI request (disk) [key: '{cache_key}']")
                    logger.info(f"CACHE HIT -> no AI request (disk) [key: '{cache_key}']")
                    return item["data"]
            except Exception as e:
                logger.warning(f"Error reading disk cache '{disk_file}': {str(e)}")

        # 3. Check Firestore Database
        if self.firestore_db:
            try:
                doc_ref = self.firestore_db.collection("ai_analysis_cache").document(cache_key).get()
                if doc_ref.exists:
                    item = doc_ref.to_dict()
                    if item and item.get("status") == "completed" and item.get("data"):
                        _memory_cache[cache_key] = item
                        # Write to disk cache for fast future reads
                        try:
                            with open(disk_file, "w", encoding="utf-8") as f:
                                json.dump(item, f, indent=2)
                        except Exception:
                            pass

                        safe_print(f"CACHE HIT -> no AI request (firestore) [key: '{cache_key}']")
                        logger.info(f"CACHE HIT -> no AI request (firestore) [key: '{cache_key}']")
                        return item["data"]
            except Exception as e:
                logger.warning(f"Firestore cache lookup failed for key '{cache_key}': {str(e)}")

        safe_print(f"CACHE MISS -> generating [key: '{cache_key}']")
        logger.info(f"CACHE MISS -> generating [key: '{cache_key}']")
        return None

    def set_pending_status(self, cache_key: str, section: str, user_id: str, document_ids: List[str]):
        """Records status='pending' before starting LLM generation."""
        record = {
            "cache_key": cache_key,
            "section": section,
            "user_id": user_id,
            "document_ids": document_ids,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        _memory_cache[cache_key] = record

    def save_result(
        self,
        cache_key: str,
        section: str,
        user_id: str,
        document_ids: List[str],
        data: Dict[str, Any],
    ):
        """
        Saves a successfully generated result with status='completed' to memory, disk, and Firestore.
        """
        now_iso = datetime.utcnow().isoformat()
        record = {
            "cache_key": cache_key,
            "section": section,
            "user_id": user_id,
            "document_ids": document_ids,
            "status": "completed",
            "data": data,
            "created_at": now_iso,
            "updated_at": now_iso,
        }

        # 1. In-Memory Save
        _memory_cache[cache_key] = record

        # 2. Disk Save
        disk_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
        try:
            with open(disk_file, "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to write disk cache file '{disk_file}': {str(e)}")

        # 3. Firestore Save
        if self.firestore_db:
            try:
                self.firestore_db.collection("ai_analysis_cache").document(cache_key).set(record)
            except Exception as e:
                logger.warning(f"Firestore cache save failed for key '{cache_key}': {str(e)}")

        safe_print(f"CACHE SAVED -> result stored [key: '{cache_key}']")
        logger.info(f"CACHE SAVED -> result stored [key: '{cache_key}']")

    def mark_failed(self, cache_key: str, error_message: str):
        """Marks cache status='failed' so failed responses are not stored as valid results."""
        record = {
            "cache_key": cache_key,
            "status": "failed",
            "error_message": error_message,
            "updated_at": datetime.utcnow().isoformat(),
        }
        _memory_cache[cache_key] = record
        # Remove disk cache file if any exists
        disk_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
        if os.path.exists(disk_file):
            try:
                os.remove(disk_file)
            except Exception:
                pass
        logger.warning(f"Generation failed for key '{cache_key}': {error_message}")

    def invalidate_document_cache(self, document_id: str, user_id: Optional[str] = None):
        """
        Invalidates all cached results associated with document_id when a document is uploaded, replaced, or deleted.
        """
        safe_print(f"INPUT CHANGED -> regenerating (invalidating cache for doc '{document_id}')")
        logger.info(f"INPUT CHANGED -> regenerating (invalidating cache for doc '{document_id}')")

        # 1. Clear Memory Cache
        keys_to_del = [
            k for k, v in _memory_cache.items()
            if document_id in k or (isinstance(v.get("document_ids"), list) and document_id in v.get("document_ids", []))
        ]
        for k in keys_to_del:
            _memory_cache.pop(k, None)

        # 2. Clear Disk Cache Files
        if os.path.exists(CACHE_DIR):
            for fname in os.listdir(CACHE_DIR):
                if document_id in fname and fname.endswith(".json"):
                    try:
                        os.remove(os.path.join(CACHE_DIR, fname))
                    except Exception:
                        pass

        # 3. Clear Firestore Cache Docs
        if self.firestore_db:
            try:
                docs = self.firestore_db.collection("ai_analysis_cache").where("document_ids", "array_contains", document_id).stream()
                for doc in docs:
                    doc.reference.delete()
            except Exception as e:
                logger.warning(f"Firestore cache invalidation note: {str(e)}")


def re_sanitize_key(key: str) -> str:
    """Sanitizes key string into a safe identifier for Firestore and filenames."""
    return "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in key)


_ai_cache_service: Optional[AICacheService] = None


def get_ai_cache_service() -> AICacheService:
    """Singleton getter for AICacheService."""
    global _ai_cache_service
    if _ai_cache_service is None:
        _ai_cache_service = AICacheService()
    return _ai_cache_service
