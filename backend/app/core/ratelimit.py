"""
Simpel in-memory rate limiter til loginflows (SEC-04).

Tæller forsøg pr. nøgle (f.eks. IP + brugernavn) i et glidende vindue.
Til et enkelt backend-instans er in-memory tilstrækkeligt; ved flere instanser
bør dette flyttes til f.eks. Redis. Dette er dokumenteret som en begrænsning.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from app.config import settings


class RateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def is_limited(self, key: str) -> bool:
        """Registrér et forsøg og returnér True, hvis grænsen er overskredet."""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            q = self._hits[key]
            while q and q[0] < cutoff:
                q.popleft()
            q.append(now)
            return len(q) > self.max_attempts

    def reset(self, key: str) -> None:
        """Nulstil ved vellykket login."""
        with self._lock:
            self._hits.pop(key, None)


login_rate_limiter = RateLimiter(
    max_attempts=settings.login_rate_limit_max,
    window_seconds=settings.login_rate_limit_window_seconds,
)
