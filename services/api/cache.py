from __future__ import annotations

import time
from copy import deepcopy
from dataclasses import dataclass
from threading import Lock
from typing import Any, Callable, Hashable


@dataclass
class _CacheRecord:
    expires_at: float
    value: Any


class TTLMemoryCache:
    """Simple in-process TTL cache for read endpoints.

    The cache stores deep copies to avoid accidental mutation across requests.
    """

    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._lock = Lock()
        self._records: dict[Hashable, _CacheRecord] = {}

    def get_or_set(self, key: Hashable, factory: Callable[[], Any]) -> Any:
        now = time.monotonic()
        with self._lock:
            record = self._records.get(key)
            if record and record.expires_at > now:
                return deepcopy(record.value)

        value = factory()
        stored = deepcopy(value)
        with self._lock:
            self._records[key] = _CacheRecord(expires_at=now + self.ttl_seconds, value=stored)
        return deepcopy(stored)

    def invalidate(self, key: Hashable) -> None:
        with self._lock:
            self._records.pop(key, None)

    def invalidate_all(self) -> None:
        with self._lock:
            self._records.clear()
