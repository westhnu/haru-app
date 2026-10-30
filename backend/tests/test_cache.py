from app.core.cache import TTLCache


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_miss_then_hit_updates_hit_rate() -> None:
    cache: TTLCache[str] = TTLCache("test", ttl_seconds=10, clock=FakeClock())

    assert cache.get("key") is None
    cache.set("key", "value")
    assert cache.get("key") == "value"

    assert (cache.hits, cache.misses, cache.hit_rate) == (1, 1, 0.5)


def test_entry_expires_after_ttl() -> None:
    clock = FakeClock()
    cache: TTLCache[str] = TTLCache("test", ttl_seconds=10, clock=clock)
    cache.set("key", "value")

    clock.now = 10.1

    assert cache.get("key") is None
