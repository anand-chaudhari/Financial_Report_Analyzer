import os
import concurrent.futures
from typing import Callable, Any, Dict, Optional
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

# Dedicated Local Background Worker Pool
# Uses max_workers=2 so background document processing runs independently of FastAPI HTTP handling threads
_worker_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="doc_worker")
_active_futures: Dict[str, concurrent.futures.Future] = {}


def submit_background_processing(
    job_id: Optional[str] = None,
    task_fn: Optional[Callable[..., Any]] = None,
    *args,
    **kwargs
) -> concurrent.futures.Future:
    """
    Submits a heavy document processing task to the local background worker pool.
    The HTTP upload endpoint returns immediately while this task runs asynchronously.
    Prevents duplicate concurrent worker tasks for the same document.
    """
    target_id = kwargs.get("document_id") or job_id or "unknown_job"
    if is_job_running(target_id):
        logger.info(f"[BackgroundWorker] Job already active for document_id='{target_id}'. Reusing existing running task.")
        return _active_futures[target_id]

    logger.info(f"[BackgroundWorker] Submitting processing job for document_id='{target_id}'")
    
    actual_fn = task_fn or kwargs.pop("task_fn", None)
    if not actual_fn:
        raise ValueError("task_fn must be provided to submit_background_processing")

    def wrapped_task():
        try:
            return actual_fn(*args, **kwargs)
        except Exception as e:
            logger.error(f"[BackgroundWorker] Uncaught exception processing document '{target_id}': {str(e)}", exc_info=True)
            raise e
        finally:
            _active_futures.pop(target_id, None)

    future = _worker_pool.submit(wrapped_task)
    _active_futures[target_id] = future
    return future


def is_job_running(document_id: str) -> bool:
    """Checks if a background processing job is actively running for the given document_id."""
    future = _active_futures.get(document_id)
    return future is not None and not future.done()
