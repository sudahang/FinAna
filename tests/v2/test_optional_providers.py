import pandas as pd
import pytest


class FakeAk:
    @staticmethod
    def stock_zh_a_hist(symbol, period, start_date, end_date, adjust):
        return pd.DataFrame({
            "日期": ["2026-08-24", "2026-08-25"],
            "开盘": [1500.0, 1515.0], "收盘": [1510.0, 1525.6],
            "最高": [1520.0, 1532.0], "最低": [1495.0, 1510.0],
            "成交量": [20000, 23456], "成交额": [3.02e9, 3.57e9],
        })


def test_akshare_kline(monkeypatch):
    import finana.datacore.providers.akshare_p as mod

    monkeypatch.setattr(mod, "_ak", FakeAk)
    p = mod.AkshareProvider()
    k = p.get_kline("600519.SH", period="d", count=2)
    assert k.source == "akshare" and len(k.bars) == 2 and k.bars[-1].close == 1525.6


def test_alltick_quote(requests_mock):
    from finana.datacore.providers.alltick import AlltickProvider

    requests_mock.get("https://quote.alltick.co/quote-stock/v2/query", json={
        "data": [{"code": "600519.SH", "last_price": 1525.6, "prev_closed": 1507.0}]})
    p = AlltickProvider(token="tok")
    q = p.get_quote("600519.SH")
    assert q.price == 1525.6
    assert q.source == "alltick"
    assert q.change_pct == pytest.approx(1.23, abs=0.01)
