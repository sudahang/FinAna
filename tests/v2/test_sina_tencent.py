import pytest


SINA_URL = "https://hq.sinajs.cn/list=sh600519"
TX_URL = "https://qt.gtimg.cn/q=sh600519"
TX_KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"

SINA_OK = (
    'var hq_str_sh600519="贵州茅台,1515.00,1507.00,1525.60,1532.00,1518.00,'
    '1525.30,1525.90,23456,3567000000,20260825150000";'
)


def test_quote_from_sina(requests_mock):
    from finana.datacore.providers.sina_tencent import SinaTencentProvider

    requests_mock.get(SINA_URL, text=SINA_OK,
                      request_headers={"Referer": "https://finance.sina.com.cn"})
    q = SinaTencentProvider().get_quote("600519.SH")
    assert q.price == 1525.6
    assert q.prev_close == 1507.0
    assert q.change_pct == pytest.approx(1.23, abs=0.01)
    assert q.source == "sina_tencent"


def test_quote_falls_back_to_tencent(requests_mock):
    from finana.datacore.providers.sina_tencent import SinaTencentProvider

    requests_mock.get(SINA_URL, status_code=403)
    requests_mock.get(TX_URL,
                      text='v_sh600519="1~贵州茅台~600519~1525.60~1507.00~1515.00~'
                           '23456~35670~'
                           '0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~'
                           '1532.00~1518.00~0~23456~35670~'
                           '0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0";')
    q = SinaTencentProvider().get_quote("600519.SH")
    assert q.price == 1525.6
    assert q.source.endswith("_tx")


def test_kline_from_tencent(requests_mock):
    from finana.datacore.providers.sina_tencent import SinaTencentProvider

    body = '{"code":0,"msg":"","data":{"sh600519":{"qfqday":[["2026-08-23","1500.00","1510.00","1520.00","1495.00","20000.00"],["2026-08-24","1510.00","1515.00","1525.00","1505.00","21000.00"],["2026-08-25","1515.00","1525.60","1532.00","1510.00","23456.00"]]}}}'
    requests_mock.get(TX_KLINE_URL, text=body)
    k = SinaTencentProvider().get_kline("600519.SH", period="d", count=3)
    assert len(k.bars) == 3 and k.bars[-1].close == 1525.6
