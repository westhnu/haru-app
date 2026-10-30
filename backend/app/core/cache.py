"""스레드 안전 인메모리 TTL 캐시.

DART Open API는 개인 키당 하루 1만 회 제한이 있어
같은 보고서를 반복 조회하지 않도록 캐시한다.
FastAPI 동기 엔드포인트는 스레드풀에서 돌기 때문에 락으로 보호한다.
"""

import threading
import time
from collections.abc import Callable, Hashable
from typing import Generic, TypeVar

import structlog

V = TypeVar("V")

logger = structlog.get_logger(__name__)


class TTLCache(Generic[V]):
    """값으로 None을 저장하지 않는다. get()의 None은 항상 '미스'를 뜻한다."""

    def __init__(
        self,
        name: str,
        ttl_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._name = name
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: dict[Hashable, tuple[float, V]] = {}
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return round(self.hits / total, 3) if total else 0.0

    def get(self, key: Hashable) -> V | None:
        with self._lock:
            entry = self._entries.get(key)
            hit = entry is not None and entry[0] > self._clock()
            if hit:
                self.hits += 1
            else:
                self.misses += 1
                self._entries.pop(key, None)
            hit_rate = self.hit_rate
        event = "cache_hit" if hit else "cache_miss"
        logger.info(event, cache=self._name, key=str(key), hit_rate=hit_rate)
        return entry[1] if hit and entry is not None else None

    def set(self, key: Hashable, value: V) -> None:
        with self._lock:
            self._entries[key] = (self._clock() + self._ttl_seconds, value)
