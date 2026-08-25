from finana.datacore.models import Bar, KLine, Quote


def test_bar_holds_values():
    b = Bar("2026-08-25", 10.0, 11.0, 9.8, 10.5, 12345, 1.3e8)
    assert b.close == 10.5


def test_kline_defaults():
    k = KLine(symbol="600519.SH", period="d", bars=[], source="test")
    assert k.period == "d" and k.bars == []
