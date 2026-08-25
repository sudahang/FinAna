"""新浪/腾讯备用行情 provider（quote 新浪主取腾讯兜底，kline 腾讯 qfq）。"""

import json
import time

from finana.datacore.http import fetch_text
from finana.datacore.models import Bar, KLine, Quote
from finana.datacore.symbols import to_sina_code

SINA_HEADERS = {"Referer": "https://finance.sina.com.cn"}
TX_KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"


class SinaTencentProvider:
    """新浪/腾讯 HTTP 行情与 K 线数据源（备用渠道，仅支持 quote/kline 域）。"""

    name = "sina_tencent"

    def _sina_quote(self, sym: str) -> Quote:
        raw = fetch_text(f"https://hq.sinajs.cn/list={to_sina_code(sym)}", headers=SINA_HEADERS)
        body = raw.split('"')[1] if '"' in raw else ""
        f = body.split(",")
        price, prev = float(f[3]), float(f[2])
        return Quote(
            symbol=sym, name=f[0], price=price, change_pct=round((price - prev) / prev * 100, 2),
            open_=float(f[1]), high=float(f[4]), low=float(f[5]),
            prev_close=prev, volume=float(f[8]), amount=float(f[9]),
            timestamp=time.time(), source=self.name,
        )

    def _tx_quote(self, sym: str) -> Quote:
        raw = fetch_text(f"https://qt.gtimg.cn/q={to_sina_code(sym)}")
        f = raw.split("~")
        price, prev = float(f[3]), float(f[4])
        return Quote(
            symbol=sym, name=f[1], price=price, change_pct=round((price - prev) / prev * 100, 2),
            open_=float(f[5]), high=float(f[33]), low=float(f[34]),
            prev_close=prev, volume=float(f[36]) * 100, amount=float(f[37]) * 1e4,
            timestamp=time.time(), source=self.name + "_tx",
        )

    def get_quote(self, sym: str) -> Quote:
        """获取实时行情：新浪主取，失败时兜底切换到腾讯。"""
        try:
            return self._sina_quote(sym)
        except Exception:
            return self._tx_quote(sym)

    def get_kline(self, sym: str, period: str = "d", count: int = 120) -> KLine:
        """从腾讯获取前复权 K 线序列。"""
        freq = {"d": "day", "w": "week", "m": "month"}.get(period, "day")
        raw = fetch_text(TX_KLINE_URL, params={"param": f"{to_sina_code(sym)},{freq},,,{count},qfq"})
        node = json.loads(raw)["data"][to_sina_code(sym)]
        rows = node.get("qfqday") or node.get(freq) or []
        bars = [Bar(r[0], float(r[1]), float(r[3]), float(r[4]), float(r[2]),
                    float(r[5]), 0.0) for r in rows]
        return KLine(symbol=sym, period=period, bars=bars[-count:], source=self.name)
