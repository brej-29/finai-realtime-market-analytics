from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Hashable


@dataclass
class CacheEntry:
    value: Any
    expires_at: datetime


class InMemoryCache:
    """Simple in-memory cache with TTL semantics.

    This cache is per-process and not shared across instances.
    """

    def __init__(self) -> None:
        self._store: dict[Hashable, CacheEntry] = {}

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def get(self, key: Hashable) -> tuple[Any, bool] | None:
        """Return (value, is_stale) if present, otherwise None.

        is_stale indicates whether the entry has passed its TTL.
        """
        entry = self._store.get(key)
        if entry is None:
            return None
        now = self._now()
        is_stale = entry.expires_at <= now
        return entry.value, is_stale

    def set(self, key: Hashable, value: Any, ttl_seconds: int) -> None:
        expires_at = self._now() + timedelta(seconds=ttl_seconds)
        self._store[key] = CacheEntry(value=value, expires_at=expires_at)

    def clear(self) -> None:
        self._store.clear()