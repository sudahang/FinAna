from __future__ import annotations

import pytest

from finana.datacore.base import DataUnavailable, DomainRouter


class _FakeProvider:
    def __init__(self, name, items=None, exc=None):
        self.name = name
        self._items = items if items is not None else []
        self._exc = exc

    def get_news(self, symbol, limit=10):
        if self._exc:
            raise self._exc
        return self._items


def _router(*providers):
    r = DomainRouter()
    for p in providers:
        r.register("news", p)
    return r


def test_aggregate_merges_and_dedupes():
    a = _FakeProvider("eastmoney", [{"title": "A"}, {"title": "B"}])
    b = _FakeProvider("sina", [{"title": "B"}, {"title": "C"}])  # B 重复应去重
    merged = _router(a, b).dispatch_aggregate("news", "get_news", "600519.SH")
    assert [m["title"] for m in merged] == ["A", "B", "C"]


def test_aggregate_continues_when_one_fails():
    a = _FakeProvider("eastmoney", exc=RuntimeError("throttled"))
    b = _FakeProvider("sina", [{"title": "C"}])
    merged = _router(a, b).dispatch_aggregate("news", "get_news", "600519.SH")
    assert [m["title"] for m in merged] == ["C"]


def test_aggregate_all_fail_raises():
    a = _FakeProvider("eastmoney", exc=RuntimeError("x"))
    b = _FakeProvider("sina", exc=RuntimeError("y"))
    with pytest.raises(DataUnavailable) as ei:
        _router(a, b).dispatch_aggregate("news", "get_news", "600519.SH")
    assert ei.value.domain == "news"
    assert len(ei.value.attempts) == 2
