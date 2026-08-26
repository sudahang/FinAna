# finana/observability.py
import json
import logging
import logging.handlers
import secrets
import statistics
import time
from contextlib import contextmanager
from contextvars import ContextVar

_trace_id: ContextVar[str] = ContextVar("trace_id", default="")
_initialized = False


def current_trace_id() -> str:
    """返回当前上下文的 trace_id，无 trace 时为空串。"""
    return _trace_id.get()


@contextmanager
def run_trace(tid: str | None = None):
    """在 trace 上下文中执行代码块，yield 新生成或指定的 trace_id。"""
    token = _trace_id.set(tid or secrets.token_hex(16))
    try:
        yield _trace_id.get()
    finally:
        _trace_id.reset(token)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": round(record.created, 3),
            "level": record.levelname,
            "logger": record.name,
            "trace_id": _trace_id.get(),
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def init_logging(settings, force: bool = False):
    """初始化 finana 根 logger（JSON 文件 + 控制台），force=True 强制重装 handler。"""
    global _initialized
    if _initialized and not force:
        return
    settings.ensure_dirs()
    root = logging.getLogger("finana")
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    root.handlers.clear()

    fh = logging.handlers.RotatingFileHandler(
        settings.logs_dir / "finana.log", maxBytes=10_000_000, backupCount=5, encoding="utf-8"
    )
    fh.setFormatter(JsonFormatter())
    root.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    root.addHandler(ch)
    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """返回挂在 finana 命名空间下的子 logger。"""
    return logging.getLogger(f"finana.{name}")


class MetricsService:
    """基于 metrics 表的指标记录与分位摘要服务。"""

    def __init__(self, conn):
        self.conn = conn

    def record(self, name: str, value: float = 1, **tags):
        """写入一条指标样本（含可选标签）。"""
        self.conn.execute(
            "INSERT INTO metrics(ts,name,value,tags_json) VALUES(?,?,?,?)",
            (time.time(), name, float(value), json.dumps(tags, ensure_ascii=False)),
        )
        self.conn.commit()

    def summary(self, name: str, since: float) -> dict:
        """返回该指标自 since 起的 count/avg/p50/p95/max 摘要。"""
        rows = self.conn.execute(
            "SELECT value FROM metrics WHERE name=? AND ts>=? ORDER BY value", (name, since)
        ).fetchall()
        vals = [r["value"] for r in rows]
        if not vals:
            return {"count": 0}
        return {
            "count": len(vals),
            "avg": round(statistics.fmean(vals), 3),
            "p50": vals[(len(vals) - 1) // 2],
            "p95": vals[min(len(vals) - 1, round(0.95 * (len(vals) - 1)))],
            "max": max(vals),
        }

    def grouped(self, since: float | None = None) -> list[dict]:
        """按指标名聚合：返回每名的 count/avg/最近样本时间。"""
        if since is None:
            rows = self.conn.execute(
                "SELECT name, COUNT(*) AS c, AVG(value) AS a, MAX(ts) AS m "
                "FROM metrics GROUP BY name ORDER BY name"
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT name, COUNT(*) AS c, AVG(value) AS a, MAX(ts) AS m "
                "FROM metrics WHERE ts>=? GROUP BY name ORDER BY name",
                (since,),
            ).fetchall()
        return [
            {"name": r["name"], "count": r["c"], "avg": round(r["a"], 3), "last_ts": r["m"]}
            for r in rows
        ]


_metrics = None


def get_metrics() -> MetricsService:
    """返回进程级单例 MetricsService（绑定默认数据库连接）。"""
    global _metrics
    if _metrics is None:
        from finana.storage.db import get_db

        _metrics = MetricsService(get_db())
    return _metrics
