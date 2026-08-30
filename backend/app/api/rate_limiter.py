import time
from collections import defaultdict
from threading import Lock
from typing import Dict, List, Any
from fastapi import HTTPException, status, Request, Depends
from .deps import get_current_user, get_optional_user
from ..utils.logger import setup_logger

logger = setup_logger("rate_limiter")

class UserRateLimiter:
    """
    Thread-safe, sliding-window per-user rate limiter for expensive AI & upload routes.
    Works seamlessly in-memory on Render single-instance services.
    """

    def __init__(self, max_requests: int = 15, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = defaultdict(list)
        self._lock = Lock()

    def check_rate_limit(self, identifier: str) -> None:
        """
        Enforces sliding-window rate limit for a given user identifier.
        Raises HTTP 429 Too Many Requests if request count exceeds limit within window.
        """
        now = time.time()
        cutoff = now - self.window_seconds

        with self._lock:
            # Filter timestamps outside the sliding window
            self._requests[identifier] = [t for t in self._requests[identifier] if t > cutoff]

            if len(self._requests[identifier]) >= self.max_requests:
                oldest_request = self._requests[identifier][0]
                retry_after = int(self.window_seconds - (now - oldest_request)) + 1
                logger.warning(
                    f"Rate limit exceeded for user '{identifier}': "
                    f"{len(self._requests[identifier])} requests in {self.window_seconds}s. Retry after {retry_after}s."
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. You have made too many requests. Please wait {retry_after} seconds before trying again.",
                    headers={"Retry-After": str(retry_after)}
                )

            # Record current request timestamp
            self._requests[identifier].append(now)


# Global instances for different operation tiers
ai_rate_limiter = UserRateLimiter(max_requests=15, window_seconds=60)
upload_rate_limiter = UserRateLimiter(max_requests=10, window_seconds=60)


async def check_ai_rate_limit(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> None:
    """Dependency enforcing AI request rate limits per authenticated user identity."""
    user_id = current_user.get("uid") or request.client.host if request.client else "anonymous"
    ai_rate_limiter.check_rate_limit(user_id)


async def check_upload_rate_limit(
    request: Request,
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> None:
    """Dependency enforcing PDF document upload rate limits per authenticated user identity."""
    user_id = current_user.get("uid") or request.client.host if request.client else "anonymous"
    upload_rate_limiter.check_rate_limit(user_id)
