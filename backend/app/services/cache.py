"""
Simple in-memory TTL cache for small RAG optimizations.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Generic, Hashable, Optional, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


@dataclass
class _CacheEntry(Generic[V]):
    value: V
    expires_at: float


class SimpleTTLCache(Generic[K, V]):
    def __init__(self, max_size: int, ttl_seconds: int) -> None:
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._data: OrderedDict[K, _CacheEntry[V]] = OrderedDict()
        self._lock = Lock()

    def get(self, key: K) -> Optional[V]:
        now = monotonic()
        with self._lock:
            entry = self._data.get(key)
            if not entry:
                return None
            if entry.expires_at < now:
                self._data.pop(key, None)
                return None
            self._data.move_to_end(key)
            return entry.value

    def set(self, key: K, value: V) -> None:
        if self._max_size <= 0 or self._ttl_seconds <= 0:
            return
        expires_at = monotonic() + self._ttl_seconds
        with self._lock:
            self._data[key] = _CacheEntry(value=value, expires_at=expires_at)
            self._data.move_to_end(key)
            while len(self._data) > self._max_size:
                self._data.popitem(last=False)

