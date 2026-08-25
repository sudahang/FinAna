"""东方财富 provider（行情/K线/搜索/资金/两融/龙虎榜/财务/新闻/板块）。"""

import json
import time
from urllib.parse import quote

from finana.datacore.http import fetch_json
from finana.datacore.models import Bar, KLine, MoneyFlowDay, Quote
from finana.datacore.symbols import to_em_secid

PUSH2 = "https://push2.eastmoney.com/api/qt/stock/get"
PUSH2_KLINE = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
PUSH2_FFLOW = "https://push2.eastmoney.com/api/qt/stock/fflow/daykline/get"
DATACENTER = "https://datacenter-web.eastmoney.com/api/data/v1/get"
DATACENTER_SEC = "https://datacenter.eastmoney.com/securities/api/data/v1/get"
F10_MAIN = "RPT_F10_FINANCE_MAINFINADATA"
SUGGEST = "https://searchapi.eastmoney.com/api/suggest/get"
CLIST = "https://push2.eastmoney.com/api/qt/clist/get"
NEWS_SEARCH = "https://search-api-web.eastmoney.com/search/jsonp"
KLT = {"d": 101, "w": 102, "m": 103}


class EastmoneyProvider:
    """东方财富数据源，提供行情、K 线与基本面等查询。"""

    name = "eastmoney"

    def _scaled(self, raw: float | None, digits_field, data: dict) -> float:
        if raw is None:
            return 0.0
        return raw / (10 ** data.get(digits_field, 2))

    def get_quote(self, sym: str) -> Quote:
        """获取实时行情快照，价格按 f59 位小数缩放。"""
        data = fetch_json(PUSH2, params={
            "secid": to_em_secid(sym),
            "fields": "f43,f44,f45,f46,f47,f48,f57,f58,f59,f60,f86",
            "invt": 2, "fltt": 1,
        })["data"]
        price = self._scaled(data.get("f43"), "f59", data)
        prev = self._scaled(data.get("f60"), "f59", data)
        change_pct = (price - prev) / prev * 100 if prev else 0.0
        return Quote(
            symbol=sym, name=data.get("f58", ""), price=price, change_pct=round(change_pct, 2),
            open_=self._scaled(data.get("f46"), "f59", data),
            high=self._scaled(data.get("f44"), "f59", data),
            low=self._scaled(data.get("f45"), "f59", data),
            prev_close=prev,
            volume=data.get("f47", 0), amount=data.get("f48", 0),
            timestamp=float(data.get("f86", time.time())), source=self.name,
        )

    def get_kline(self, sym: str, period: str = "d", count: int = 120) -> KLine:
        """获取前复权 K 线序列（klt 101/102/103 对应日/周/月）。"""
        data = fetch_json(PUSH2_KLINE, params={
            "secid": to_em_secid(sym), "klt": KLT.get(period, 101), "fqt": 1,
            "lmt": count, "end": "20500101",
            "fields1": "f1,f2,f3", "fields2": "f51,f52,f53,f54,f55,f56,f57",
        })["data"]
        bars = []
        for line in data["klines"]:
            d, o, c, h, l, v, a = line.split(",")
            bars.append(Bar(d, float(o), float(h), float(l), float(c), float(v), float(a)))
        return KLine(symbol=sym, period=period, bars=bars[-count:], source=self.name)

    def resolve(self, query: str) -> list[dict]:
        """模糊搜索股票代码，返回 [{symbol(规范形), code, name, market}]。"""
        data = fetch_json(SUGGEST, params={"input": query, "type": "14", "count": 5})
        out = []
        for item in (data.get("QuotationCodeTable", {}).get("Data") or []):
            type_name = item.get("SecurityTypeName", "")
            if "京" in type_name:
                suffix = ".BJ"
            elif "沪" in type_name or item.get("MktNum") == "1":
                suffix = ".SH"
            else:
                suffix = ".SZ"
            code = item.get("Code", "")
            out.append({
                "code": code, "name": item.get("Name"),
                "market": item.get("MktNum"), "symbol": f"{code}{suffix}",
            })
        return out

    def get_money_flow(self, sym: str, days: int = 10) -> list[MoneyFlowDay]:
        """获取个股近 N 日主力资金流。"""
        data = fetch_json(PUSH2_FFLOW, params={
            "secid": to_em_secid(sym), "klt": 101, "lmt": days,
            "fields1": "f1,f2,f3,f7", "fields2": "f51,f52",
        })["data"]
        return [MoneyFlowDay(date=r.split(",")[0], main_net=float(r.split(",")[1]), source=self.name)
                for r in data.get("klines", [])]

    def get_margin(self, sym: str, days: int = 20) -> list[dict]:
        """获取个股近 N 日两融余额明细（RPTA_WEB_RZRQ_GGMX，按 DATE 倒序）。"""
        code = sym.split(".")[0]
        data = fetch_json(DATACENTER, params={
            "reportName": "RPTA_WEB_RZRQ_GGMX", "columns": "ALL",
            "filter": f'(scode="{code}")', "sortColumns": "DATE",
            "sortTypes": "-1", "pageSize": days,
        })
        return (data.get("result") or {}).get("data") or []

    def get_lhb(self, sym: str, days: int = 30) -> list[dict]:
        """获取个股近 N 日龙虎榜记录（RPT_DAILYBILLBOARD_DETAILSNEW）。"""
        code = sym.split(".")[0]
        data = fetch_json(DATACENTER, params={
            "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW", "columns": "ALL",
            "filter": f'(SECURITY_CODE="{code}")', "sortColumns": "TRADE_DATE",
            "sortTypes": "-1", "pageSize": days,
        })
        return (data.get("result") or {}).get("data") or []

    def get_financials(self, sym: str) -> dict:
        """获取主要财务指标最新一期（datacenter RPT_F10_FINANCE_MAINFINADATA）。"""
        data = fetch_json(DATACENTER_SEC, params={
            "reportName": F10_MAIN, "columns": "ALL",
            "filter": f'(SECUCODE="{sym}")', "pageNumber": 1, "pageSize": 1,
            "sortTypes": "-1", "sortColumns": "REPORT_DATE",
            "source": "HSF10", "client": "PC",
        })
        rows = (data.get("result") or {}).get("data") or []
        return rows[0] if rows else {}

    def get_news(self, sym: str, limit: int = 10) -> list[dict]:
        """搜索个股相关新闻，返回 [{title, date, url}]。

        参数需手动百分号编码（requests 的 + 空格编码会被接口误解析），
        TLS 指纹反爬由 fetch_json 内置的 curl_cffi 兜底处理。
        """
        code = sym.split(".")[0]
        param = json.dumps({
            "uid": "", "keyword": code, "type": ["cmsArticleWebOld"], "client": "web",
            "clientVersion": "curr",
            "param": {"cmsArticleWebOld": {"searchScope": "default", "sort": "default",
                                           "pageIndex": 1, "pageSize": limit}},
        }, separators=(",", ":"))
        data = fetch_json(f"{NEWS_SEARCH}?cb=&param={quote(param, safe='')}")
        arts = (data.get("result") or {}).get("cmsArticleWebOld") or []
        return [{"title": a.get("title", "").replace("<em>", "").replace("</em>", ""),
                 "date": a.get("date"), "url": a.get("url")} for a in arts]

    def get_sector_snapshot(self, limit: int = 50) -> list[dict]:
        """获取行业板块快照列表（fs=m:90+t:2），按涨幅排序。"""
        data = fetch_json(CLIST, params={
            "pn": 1, "pz": limit, "po": 1, "np": 1, "fltt": 2, "fid": "f3",
            "fs": "m:90 t:2", "fields": "f2,f3,f12,f14",
        })
        return [{"code": d.get("f12"), "name": d.get("f14"), "change_pct": d.get("f3")}
                for d in (data.get("data", {}) or {}).get("diff", [])]
