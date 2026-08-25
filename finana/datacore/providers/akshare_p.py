"""AKShare 可选 K 线 provider（akshare 未安装时构造抛 ImportError 由组装方跳过）。"""

from datetime import date, timedelta

from finana.datacore.models import Bar, KLine

try:
    import akshare as _ak
except ImportError:
    _ak = None

_PERIOD_MAP = {"d": "daily", "w": "weekly", "m": "monthly"}


class AkshareProvider:
    """AKShare A 股历史 K 线数据源（可选渠道）。"""

    name = "akshare"

    def __init__(self):
        if _ak is None:
            raise ImportError("akshare 未安装: pip install akshare")

    def get_kline(self, sym: str, period: str = "d", count: int = 120) -> KLine:
        """从 akshare 获取前复权日/周/月 K 线，返回最近 count 根。"""
        code = sym.split(".")[0]
        start = (date.today() - timedelta(days=int(count * 1.6))).strftime("%Y%m%d")
        end = date.today().strftime("%Y%m%d")
        df = _ak.stock_zh_a_hist(
            symbol=code, period=_PERIOD_MAP.get(period, "daily"),
            start_date=start, end_date=end, adjust="qfq",
        )
        df = df.tail(count)
        bars = [
            Bar(str(r["日期"]), float(r["开盘"]), float(r["最高"]), float(r["最低"]),
                float(r["收盘"]), float(r["成交量"]), float(r.get("成交额", 0.0)))
            for _, r in df.iterrows()
        ]
        return KLine(symbol=sym, period=period, bars=bars, source=self.name)
