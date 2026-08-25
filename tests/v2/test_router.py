import pytest

from finana.datacore.base import DataUnavailable, DomainRouter, TTLCache


class Ok:
    name = "ok"

    def get_x(self, v):
        return v * 2


class Bad:
    name = "bad"

    def __init__(self):
        self.fails = 0

    def get_x(self, v):
        self.fails += 1
        raise RuntimeError("boom")


def test_ttl_cache_expiry():
    clock = [0.0]
    c = TTLCache(time_func=lambda: clock[0])
    c.put("k", 1, ttl=10)
    assert c.get("k") == 1
    clock[0] += 11
    assert c.get("k") is None


def test_router_success_first_provider():
    r = DomainRouter()
    r.register("x", Ok())
    assert r.dispatch("x", "get_x", 21, cache_ttl=None) == 42


def test_router_failover_to_next():
    bad, ok = Bad(), Ok()
    r = DomainRouter()
    r.register("x", bad)
    r.register("x", ok)
    assert r.dispatch("x", "get_x", 5) == 10


def test_router_all_fail_raises():
    r = DomainRouter()
    r.register("x", Bad())
    with pytest.raises(DataUnavailable) as ei:
        r.dispatch("x", "get_x", 1)
    assert any("bad" in a for a in ei.value.attempts)


def test_router_skips_open_breaker():
    bad = Bad()
    r = DomainRouter()
    r.register("x", bad)
    r.register("x", Ok())
    for _ in range(5):
        r.dispatch("x", "get_x", 1)
    assert bad.fails == 3
