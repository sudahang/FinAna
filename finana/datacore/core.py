"""DataCore 门面：统一数据入口、缓存策略与健康报告。"""

from functools import lru_cache

from finana.config import get_settings
from finana.datacore.base import DomainRouter, TTLCache
from finana.datacore.symbols import normalize_symbol

_TTL = {"quote": 30, "kline": 300, "moneyflow": 300}
_DEFAULT_TTL = 1800

_DOMAIN_METHODS = [
    ("quote", "get_quote"), ("kline", "get_kline"), ("moneyflow", "get_money_flow"),
    ("margin", "get_margin"), ("lhb", "get_lhb"), ("financials", "get_financials"),
    ("news", "get_news"), ("sector", "get_sector_snapshot"),
]


class DataCore:
    """多渠道财经数据门面，按域路由 failover 并带 TTL 缓存。"""

    def __init__(self, settings=None):
        from finana.datacore import registry

        self.settings = settings or get_settings()
        providers = registry.build_providers(self.settings)
        self.cache = TTLCache(default_ttl=_DEFAULT_TTL)
        self._routers = {domain: DomainRouter() for domain, _ in _DOMAIN_METHODS}
        for domain, method in _DOMAIN_METHODS:
            for p in providers:
                if hasattr(p, method):
                    self._routers[domain].register(domain, p)

    def _call(self, domain, method, *args, symbol_first=True):
        if symbol_first and args:
            args = (normalize_symbol(args[0]),) + args[1:]
        ttl = _TTL.get(domain, _DEFAULT_TTL)
        return self._routers[domain].dispatch(domain, method, *args, cache=self.cache, cache_ttl=ttl)

    def _call_aggregate(self, domain, method, *args, symbol_first=True):
        if symbol_first and args:
            args = (normalize_symbol(args[0]),) + args[1:]
        ttl = _TTL.get(domain, _DEFAULT_TTL)
        return self._routers[domain].dispatch_aggregate(domain, method, *args, cache=self.cache, cache_ttl=ttl)

    def get_quote(self, symbol):
        """获取实时行情快照。"""
        return self._call("quote", "get_quote", symbol)

    def get_kline(self, symbol, period="d", count=120):
        """获取历史 K 线序列。"""
        return self._call("kline", "get_kline", symbol, period, count)

    def get_money_flow(self, symbol, days=10):
        """获取资金流向日序列。"""
        return self._call("moneyflow", "get_money_flow", symbol, days)

    def get_margin(self, symbol, days=20):
        """获取融资融券日序列。"""
        return self._call("margin", "get_margin", symbol, days)

    def get_lhb(self, symbol, days=30):
        """获取龙虎榜记录列表。"""
        return self._call("lhb", "get_lhb", symbol, days)

    def get_financials(self, symbol):
        """获取公司财务指标字典。"""
        return self._call("financials", "get_financials", symbol)

    def get_news(self, symbol, limit=10):
        """获取个股新闻列表（聚合东财个股新闻与新浪市场要闻，按标题去重）。"""
        return self._call_aggregate("news", "get_news", symbol, limit)

    def get_sector_snapshot(self, limit=50):
        """获取行业板块快照列表（多源聚合）。"""
        return self._call_aggregate("sector", "get_sector_snapshot", limit, symbol_first=False)

    def health(self) -> list[dict]:
        """输出每个 provider×domain 的熔断状态、失败数与最近错误信息。"""
        out = []
        for domain, router in self._routers.items():
            for p in router.chain(domain):
                br = router._breakers.get((domain, p.name)) or CircuitBreakerView()
                out.append({"provider": p.name, "domain": domain, "state": br.state,
                            "failures": br.failures, "last_error": br.last_error,
                            "last_error_at": br.last_error_at})
        return out


class CircuitBreakerView:
    state, failures, last_error, last_error_at = "closed", 0, "", 0.0


@lru_cache
def get_datacore() -> DataCore:
    """返回进程级单例 DataCore。"""
    return DataCore()
