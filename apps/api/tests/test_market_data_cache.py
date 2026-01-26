from __future__ import annotations

import time

from app.services.market_data.cache import InMemoryCache


def test_in_memory_cache_ttl() -> None:
    cache = InMemoryCache()
    cache.set("key", "value", ttl_seconds=1)

    value, is_stale = cache.get("key")  # type: ignore[misc]
    assert value == "value"
    assert is_stale is False

    time.sleep(1.1)
    value, is_stale = cache.get("key")  # type: ignore[misc]
    assert value == "value"
    assert is_stale is True