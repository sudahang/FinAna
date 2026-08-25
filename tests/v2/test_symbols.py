import pytest

from finana.datacore.symbols import normalize_symbol, to_em_secid, to_sina_code


@pytest.mark.parametrize("raw,expected", [
    ("600519", "600519.SH"),
    ("sh600519", "600519.SH"),
    ("600519.SH", "600519.SH"),
    ("000001", "000001.SZ"),
    ("sz000001", "000001.SZ"),
    ("300750", "300750.SZ"),
    ("688981", "688981.SH"),
    ("sh000001", "000001.SH"),
    ("430047", "430047.BJ"),
])
def test_normalize(raw, expected):
    assert normalize_symbol(raw) == expected


def test_normalize_index_vs_stock():
    assert normalize_symbol("000001.SZ") != normalize_symbol("000001.SH")


def test_secid_mapping():
    assert to_em_secid("600519.SH") == "1.600519"
    assert to_em_secid("000001.SZ") == "0.000001"


def test_sina_code():
    assert to_sina_code("600519.SH") == "sh600519"
    assert to_sina_code("000001.SZ") == "sz000001"
