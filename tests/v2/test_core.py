import pytest

from finana.datacore.base import CircuitBreaker, DataUnavailable


class StubP:
    def __init__(self, name, fail=False):
        self.name, self.fail = name, fail
        self.calls = 0

    def get_quote(self, sym):
        self.calls += 1
        if self.fail:
            raise RuntimeError("down")
        from finana.datacore.models import Quote

        return Quote(sym, "stub", 1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0.0, source=self.name)

    def get_kline(self, sym, period="d", count=10):
        from finana.datacore.models import KLine

        return KLine(sym, period, [], source=self.name)


def _make_core(first, second):
    from finana.datacore.core import DataCore

    core = DataCore.__new__(DataCore)
    from finana.datacore.base import DomainRouter, TTLCache

    core.cache = TTLCache(default_ttl=60)
    quote_r, kline_r = DomainRouter(), DomainRouter()
    for p in (first, second):
        if hasattr(p, "get_quote"):
            quote_r.register("quote", p)
        if hasattr(p, "get_kline"):
            kline_r.register("kline", p)
    core._routers = {"quote": quote_r, "kline": kline_r}
    return core


def test_normalize_inside_facade():
    core = _make_core(StubP("a"), StubP("b"))
    q = core.get_quote("600519")
    assert q.symbol == "600519.SH"


def test_failover_and_caching():
    dead, alive = StubP("dead", fail=True), StubP("live")
    core = _make_core(dead, alive)
    q1 = core.get_quote("600519.SH")
    q2 = core.get_quote("600519.SH")
    assert q1.source == "live"
    assert alive.calls == 1
    assert dead.calls == 1


def test_health_reports_states():
    core = _make_core(StubP("a"), StubP("b", fail=True))
    core.get_kline("600519.SH")
    states = {(h["provider"], h["domain"]) for h in core.health()}
    assert any(d == "kline" for _, d in states)


def test_unavailable_when_empty_chain():
    core = _make_core(StubP("a"), StubP("b"))
    core._routers["quote"]._domains["quote"] = []
    with pytest.raises(DataUnavailable):
        core.get_quote("600519.SH")


def test_build_providers_tolerates_settings_without_fields():
    from types import SimpleNamespace
    from finana.datacore import registry

    providers = registry.build_providers(SimpleNamespace())
    names = [p.name for p in providers]
    assert "eastmoney" in names and "sina_tencent" in names
    assert "alltick" not in names
