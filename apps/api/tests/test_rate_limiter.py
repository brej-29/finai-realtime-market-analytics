from __future__ import annotations

import time

from app.core.errors import RateLimitExceededError
from app.services.market_data.rate_limiter import RateLimitGuard


def test_rate_limiter_enforces_capacity() -> None:
    guard = RateLimitGuard(capacity=2, refill_per_second=0.0)

    guard.acquire()
    guard.acquire()

    try:
        guard.acquire()
        assert False, "Expected RateLimitExceededError"
    except RateLimitExceededError:
        pass

    # After some time with zero refill rate, still no tokens
    time.sleep(0.1)
    try:
        guard.acquire()
        assert False, "Expected RateLimitExceededError"
    except RateLimitExceededError:
        pass