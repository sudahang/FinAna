"""DataCore 基础组件：熔断器、TTL 缓存与域路由。"""

import time
from collections import OrderedDict

from finana.observability import get_logger, get_metrics

log = get_logger("datacore")


class DataUnavailable(Exception):
    """某数据域所有渠道均失败时抛出，携带 domain 与 attempts 尝试记录。"""

    def __init__(self, domain: str, attempts: list[str]):
        self.domain = domain
        self.attempts = attempts
        super().__init__(f"{domain} 所有渠道失败: {attempts}")


class CircuitBreaker:
    """按失败阈值熔断、冷却后半开恢复的熔断器。"""

    def __init__(self, threshold: int = 3, cooldown: float = 300.0, time_func=time.monotonic):
        self.threshold = threshold
        self.cooldown = cooldown
        self.time_func = time_func
        self.failures = 0
        self.opened_at = 0.0
        self.last_error: str = ""
        self.last_error_at: float = 0.0

    @property
    def state(self) -> str:
        """返回当前状态：closed / open / half-open。"""
        if self.failures < self.threshold:
            return "closed"
        if self.time_func() - self.opened_at >= self.cooldown:
            return "half-open"
        return "open"

    def allow(self) -> bool:
        """判断当前是否允许调用渠道（非 open 状态）。"""
        return self.state != "open"

    def record_success(self):
        """记录一次成功，重置连续失败计数。"""
        self.failures = 0

    def record_failure(self, err: Exception | None = None):
        """记录一次失败，达到阈值时打开熔断器。"""
        self.failures += 1
        if err is not None:
            self.last_error = f"{type(err).__name__}: {err}"
        self.last_error_at = self.time_func()
        if self.failures >= self.threshold:
            self.opened_at = self.time_func()


class TTLCache:
    """带过期时间与容量上限的 LRU 缓存。"""

    def __init__(self, default_ttl: float = 60.0, time_func=time.monotonic, max_items: int = 512):
        self.default_ttl = default_ttl
        self.time_func = time_func
        self.max_items = max_items
        self._store: OrderedDict = OrderedDict()

    def put(self, key, value, ttl: float | None = None):
        """写入缓存项，ttl 为空时使用默认过期时间。"""
        self._store[key] = (self.time_func() + (ttl or self.default_ttl), value)
        self._store.move_to_end(key)
        while len(self._store) > self.max_items:
            self._store.popitem(last=False)

    def get(self, key):
        """读取缓存项，命中且未过期返回值，否则返回 None。"""
        item = self._store.get(key)
        if not item:
            return None
        exp, val = item
        if self.time_func() >= exp:
            del self._store[key]
            return None
        return val


class DomainRouter:
    """按注册顺序在多渠道间 failover 的域路由器。"""

    def __init__(self):
        self._domains: dict[str, list] = {}
        self._breakers: dict[tuple, CircuitBreaker] = {}

    def register(self, domain: str, provider):
        """向指定数据域追加一个渠道 provider（按注册顺序生效）。"""
        self._domains.setdefault(domain, []).append(provider)

    def _breaker(self, key: tuple) -> CircuitBreaker:
        if key not in self._breakers:
            self._breakers[key] = CircuitBreaker()
        return self._breakers[key]

    def chain(self, domain: str) -> list:
        """返回指定域已注册的渠道列表。"""
        return self._domains.get(domain, [])

    def dispatch(
        self,
        domain: str,
        method: str,
        *args,
        cache: TTLCache | None = None,
        cache_ttl: float | None = None,
    ):
        """依次尝试可用渠道调用 method，成功写缓存并记 metric，全部失败抛 DataUnavailable。"""
        cache_key = (domain, method, args)
        if cache is not None:
            hit = cache.get(cache_key)
            if hit is not None:
                return hit
        attempts: list[str] = []
        for provider in self.chain(domain):
            br = self._breaker((domain, provider.name))
            if not br.allow():
                attempts.append(f"{provider.name}:skip(open)")
                continue
            t0 = time.monotonic()
            try:
                result = getattr(provider, method)(*args)
                elapsed_ms = (time.monotonic() - t0) * 1000
                br.record_success()
                get_metrics().record(f"datacore.{domain}.{provider.name}.latency_ms", elapsed_ms, method=method)
                if cache is not None:
                    cache.put(cache_key, result, cache_ttl)
                return result
            except Exception as e:
                br.record_failure(e)
                attempts.append(f"{provider.name}:{type(e).__name__}")
                log.warning("provider failed domain=%s provider=%s err=%s", domain, provider.name, e)
                get_metrics().record(f"datacore.{domain}.{provider.name}.errors", 1)
        raise DataUnavailable(domain, attempts)
