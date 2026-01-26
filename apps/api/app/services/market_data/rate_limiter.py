from __future__ import annotations

import time
from dataclasses import dataclass

from app.core.errors import RateLimitExceededError


@dataclass
class RateLimitGuard:
    """Token-bucket style rate limiter.

    Designed to be simple and per-process. It is not distributed across instances.
    """

    capacity: int
    refill_per_second: float

    def __post_init__(self) -> None:
        self._tokens: float = float(self.capacity)
        self._last_refill: float = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._last_refill = now

        refill_amount = elapsed * self.refill_per_second
        self._tokens = min(self.capacity, self._tokens + refill_amount)

    def acquire(self) -> None:
        """Consume one token or raise RateLimitExceededError if none are available."""
        self._refill()
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return
        raise RateLimitExceededError("Rate limit exceeded for provider call.")