import asyncio
import json

import pytest
from fastmcp import Client


def _stub_core():
    from finana.datacore.models import Quote

    class Core:
        def get_quote(self, symbol):
            return Quote(symbol, "贵州茅台", 1525.6, 1.23, 1515.0, 1532.0, 1518.0,
                         1507.0, 23456.0, 3.567e9, 0.0, source="stub")

        def get_news(self, symbol, limit=10):
            return [{"title": "t", "date": "2026-08-25", "url": "u"}][:limit]

    return Core()


def _run(coro):
    return asyncio.run(coro)


def test_tools_registered():
    from finana.mcp_server.server import build_server

    async def _names():
        async with Client(build_server(core=_stub_core())) as c:
            return {t.name for t in await c.list_tools()}

    got = _run(_names())
    assert {"get_realtime_quote", "get_kline", "get_money_flow", "get_margin",
            "get_lhb", "get_financials", "get_stock_news",
            "get_sector_snapshot"} <= got


def test_quote_tool_returns_compact_json():
    from finana.mcp_server.server import build_server

    async def _call():
        async with Client(build_server(core=_stub_core())) as c:
            res = await c.call_tool("get_realtime_quote", {"symbol": "600519.SH"})
        return res.content[0].text

    data = json.loads(_run(_call()))
    assert data["price"] == 1525.6 and data["source"] == "stub"


def test_unavailable_degrades_gracefully():
    from finana.datacore.base import DataUnavailable
    from finana.mcp_server.server import build_server

    class Boom:
        def get_quote(self, symbol):
            raise DataUnavailable("quote", ["eastmoney:error"])

    async def _call():
        async with Client(build_server(core=Boom())) as c:
            res = await c.call_tool("get_realtime_quote", {"symbol": "600519.SH"})
        return res.content[0].text

    text = _run(_call())
    assert text.startswith("ERROR:") and "quote" in text
