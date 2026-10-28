"""Small in-memory sliding-window rate limiter.

Fine for a single process (local dev, single container). When we run several
workers/containers this must move to Redis; tracked in DECISIONS.md.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.core.config import get_settings


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> int | None:
        """Record a hit. Return None if allowed, else seconds until retry."""
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] >= window_seconds:
                q.popleft()
            if len(q) >= limit:
                return max(1, int(window_seconds - (now - q[0])) + 1)
            q.append(now)
            return None

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = SlidingWindowLimiter()


def auth_rate_limit(request: Request) -> None:
    s = get_settings()
    client = request.client.host if request.client else "unknown"
    key = f"{client}:{request.url.path}"
    retry_after = limiter.check(key, s.auth_rate_limit_attempts, s.auth_rate_limit_window_seconds)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )


def llm_rate_limit(request: Request) -> None:
    """Guards endpoints that can spend LLM tokens (question generation, answer scoring)."""
    s = get_settings()
    client = request.client.host if request.client else "unknown"
    retry_after = limiter.check(f"llm:{client}", s.llm_rate_limit_per_minute, 60)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Try again shortly.",
            headers={"Retry-After": str(retry_after)},
        )
