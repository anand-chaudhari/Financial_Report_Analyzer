import os
import concurrent.futures
from typing import Callable, Any, Dict, Optional
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

# Dedicated Local Background Worker Pool
# Uses max_workers=2 so background PDF processing runs independently of FastAPI HTTP handling threads
_worker_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="doc_worker")
_active_futures: Dict[str, concurrent.futures.Future] = {}


def submit_background_processing(document_id: str, task_fn: Callable[..., Any], *args, **kwargs) -> concurrent.futures.Future:
    """
    Submits a heavy PDF processing task to the local background worker pool.
    The HTTP upload endpoint returns immediately while this task runs asynchronously.
    """
    logger.info(f"[BackgroundWorker] Submitting processing job for document_id='{document_id}'")
    
    def wrapped_task():
        try:
            return task_fn(*args, **kwargs)
        except Exception as e:
            logger.error(f"[BackgroundWorker] Uncaught exception processing document '{document_id}': {str(e)}", exc_info=True)
            raise e
        finally:
            _active_futures.pop(document_id, None)

    future = _worker_pool.submit(wrapped_task)
    _active_futures[document_id] = future
    return future


def is_job_running(document_id: str) -> bool:
    """Checks if a background processing job is actively running for the given document_id."""
    future = _active_futures.get(document_id)
    return future is not None and not future.done()
