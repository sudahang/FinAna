"""AllTick 可选实时行情 provider（需配置 token，未配置时由组装方跳过）。"""

import time

from finana.datacore.http import fetch_json
from finana.datacore.models import Quote

QUERY_URL = "https://quote.alltick.co/quote-stock/v2/query"


class AlltickProvider:
    """AllTick 实时行情快照数据源（可选渠道）。"""

    name = "alltick"

    def __init__(self, token: str):
        if not token:
            raise ImportError("alltick token 未配置(FINANA_ALLTICK_TOKEN)")
        self.token = token

    def get_quote(self, sym: str) -> Quote:
        """从 AllTick 查询最新价并计算涨跌幅，字段名以 Task 11 实测为准。"""
        data = fetch_json(QUERY_URL, params={"code": sym.lower(), "token": self.token})
        row = (data.get("data") or [{}])[0]
        price = float(row.get("last_price") or 0)
        prev = float(row.get("prev_closed") or 0)
        return Quote(
            symbol=sym, name=row.get("code", sym), price=price,
            change_pct=round((price - prev) / prev * 100, 2) if prev else 0.0,
            open_=float(row.get("open") or 0), high=float(row.get("high") or 0),
            low=float(row.get("low") or 0), prev_close=prev,
            volume=float(row.get("volume") or 0), amount=0.0,
            timestamp=time.time(), source=self.name,
        )
