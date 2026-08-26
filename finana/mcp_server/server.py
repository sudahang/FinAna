import functools
import json
from dataclasses import asdict, is_dataclass

from fastmcp import FastMCP

from finana.config import get_settings
from finana.datacore.base import DataUnavailable
from finana.observability import get_logger

log = get_logger("mcp")


def _serialize(obj):
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, list):
        return [_serialize(x) for x in obj]
    return obj


def build_server(core=None, memory=None) -> FastMCP:
    mcp = FastMCP("finana")
    dc = core
    mem = memory

    def _core():
        nonlocal dc
        if dc is None:
            from finana.datacore.core import get_datacore

            dc = get_datacore()
        return dc

    def _memory():
        nonlocal mem
        if mem is None:
            from finana.memory.service import MemoryService
            from finana.storage.db import connect

            mem = MemoryService(connect(get_settings().database_path))
        return mem

    def wrap(domain):
        def deco(fn):
            @functools.wraps(fn)
            def inner(*args, **kwargs):
                try:
                    return json.dumps(_serialize(fn(*args, **kwargs)), ensure_ascii=False)
                except DataUnavailable as e:
                    return f"ERROR: {domain} 数据暂不可用({','.join(e.attempts)})，请基于已有信息谨慎判断"
            return mcp.tool(inner)
        return deco

    @wrap("quote")
    def get_realtime_quote(symbol: str) -> str:
        """获取A股实时行情快照(价格/涨跌幅/量额)。"""
        return _core().get_quote(symbol)

    @wrap("kline")
    def get_kline(symbol: str, period: str = "d", count: int = 120) -> str:
        """获取历史K线(前复权)。period: d/w/m。"""
        return _core().get_kline(symbol, period=period, count=count).bars

    @wrap("moneyflow")
    def get_money_flow(symbol: str, days: int = 10) -> str:
        """获取个股主力资金净流入日线序列。"""
        return _core().get_money_flow(symbol, days=days)

    @wrap("margin")
    def get_margin(symbol: str, days: int = 20) -> str:
        """获取融资融券余额明细。"""
        return _core().get_margin(symbol, days=days)

    @wrap("lhb")
    def get_lhb(symbol: str, days: int = 30) -> str:
        """获取龙虎榜上榜记录。"""
        return _core().get_lhb(symbol, days=days)

    @wrap("financials")
    def get_financials(symbol: str) -> str:
        """获取核心财务指标(营收/净利/ROE等最新期)。"""
        return _core().get_financials(symbol)

    @wrap("news")
    def get_stock_news(symbol: str, limit: int = 10) -> str:
        """获取个股近期新闻标题列表。"""
        return _core().get_news(symbol, limit=limit)

    @wrap("sector")
    def get_sector_snapshot(limit: int = 50) -> str:
        """获取行业板块涨跌概览。"""
        return _core().get_sector_snapshot(limit=limit)

    @mcp.tool()
    def recall_memory(query: str, symbol: str = "", layers: str = "") -> str:
        """检索分层记忆并回灌上下文。query 为检索词；symbol 可选限定标的；layers 可选(l2/l3/l4 逗号分隔，默认全查)。"""
        svc = _memory()
        out: dict = {}
        if not symbol or "l2" in (layers or "l2,l3,l4"):
            if symbol:
                inst = svc.get_instrument(symbol)
                if inst is not None:
                    out["instrument"] = inst
        if not symbol or "l3" in (layers or "l2,l3,l4"):
            out["semantic"] = svc.search_semantic(query or symbol, k=5)
        if "l4" in (layers or "l2,l3,l4"):
            out["profile"] = svc.get_profile()
        return json.dumps(out, ensure_ascii=False, default=str)

    @mcp.tool()
    def save_analysis_memory(symbol: str, content: str, tags: str = "") -> str:
        """写入一条语义记忆(分析结论/方法论卡片)。symbol 用于关联标的标签；tags 逗号分隔。"""
        svc = _memory()
        sid = svc.remember_semantic(content, tags=tags or symbol)
        if symbol:
            svc.upsert_instrument(symbol, conclusion=content[:200])
        return json.dumps({"saved_id": sid}, ensure_ascii=False)

    @mcp.tool()
    def get_user_profile() -> str:
        """返回当前用户画像(风险偏好/风格/关注列表/反馈)。"""
        return json.dumps(_memory().get_profile(), ensure_ascii=False)

    return mcp


mcp = None


def _default():
    global mcp
    if mcp is None:
        mcp = build_server()
    return mcp


if __name__ == "__main__":
    _default().run()
