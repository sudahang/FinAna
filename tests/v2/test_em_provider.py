import json
from pathlib import Path

import pytest
import requests_mock as rm_module

FIXTURES = Path(__file__).parent / "em_fixtures"


def _load(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def em():
    from finana.datacore.providers.em import EastmoneyProvider

    return EastmoneyProvider()


def test_get_quote(em, requests_mock):
    requests_mock.get(rm_module.ANY, text=_load("quote_600519.json"))
    q = em.get_quote("600519.SH")
    assert q.symbol == "600519.SH"
    assert abs(q.price - 1525.6) < 0.01
    assert q.change_pct == pytest.approx(1.23, abs=0.01)
    assert q.source == "eastmoney"


def test_get_kline(em, requests_mock):
    requests_mock.get(rm_module.ANY, text=_load("kline_600519.json"))
    k = em.get_kline("600519.SH", period="d", count=3)
    assert k.source == "eastmoney"
    assert len(k.bars) == 3
    assert k.bars[-1].close > 0


def test_resolve(em, requests_mock):
    requests_mock.get(rm_module.ANY, text=_load("suggest_maotai.json"))
    out = em.resolve("茅台")
    assert out and out[0]["name"].startswith("贵州茅台")


def test_money_flow_parses(em, requests_mock):
    requests_mock.get(rm_module.ANY, text=_load("fflow.json"))
    days = em.get_money_flow("600519.SH", days=2)
    assert len(days) == 2 and days[0].main_net != 0
