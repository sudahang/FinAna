# FinAna v2 · Plan 1：基础设施与数据核心库 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 FinAna v2 的地基——配置、SQLite、日志指标、可插拔多渠道 A 股数据核心库（含熔断降级）、finana-doctor 健康探测、FastMCP 数据工具服务器。

**Architecture:** 纯 Python 包 `finana/`；数据域（行情/K线/资金/财务/新闻/板块）各自定义 Provider 接口，多渠道实现按可配置优先级链式调用，逐渠道熔断降级；对外经 FastMCP stdio 暴露为模型工具。

**Tech Stack:** Python ≥3.10、pydantic-settings、requests、SQLite(WAL)、FastMCP、pytest + requests-mock。

**Spec:** `docs/superpowers/specs/2026-08-25-finana-v2-deepseek-harness-design.md`（§4 数据层、§9 错误处理、§10 可观测性、§11 测试策略、§12 结构）

## Global Constraints

- Python ≥3.10；所有命令在仓库根目录、`venv` 激活状态下执行（macOS/zsh）
- v2 测试统一放 `tests/v2/`，运行方式固定为 `python -m pytest tests/v2/<file> -v`（旧 tests/ 下遗留用例在 Plan 3 才清理，勿动）
- HTTP 一律用 `requests`（不引入 httpx）；数据请求必须带超时（默认 10s）
- SQLite 启用 WAL；所有表定义集中在 `finana/storage/schema.sql`，幂等 `CREATE TABLE IF NOT EXISTS`
- 代码不加注释（保持与现有仓库风格一致），公共 API 用简短 docstring
- 提交信息风格沿用仓库历史：短祈使句，如 `feat: add circuit breaker`
- 本计划不引入 `deepseek-harness-sdk`（Plan 2 才用），不删任何旧代码
- 渠道端点以 2026-08 调研为准写入，Task 11 的实测 spike 负责最终校准；凡实测不符，修 URL/解析器并同步更新对应 fixture

---

### Task 1: 项目脚手架、依赖与配置

**Files:**
- Create: `finana/__init__.py`、`finana/config.py`、`finana/py.typed`（空）、根 `conftest.py`、`.env.example`
- Modify: `requirements.txt`、`requirements-dev.txt`
- Test: `tests/v2/test_config.py`

**Interfaces:**
- Produces: `finana.config.Settings`（字段见下）、`finana.config.get_settings() -> Settings`（lru_cache 单例）。后续所有任务经 `get_settings()` 取配置。

- [ ] **Step 1: 写失败测试**

```python
# tests/v2/test_config.py
from pathlib import Path


def test_settings_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANA_HOME", str(tmp_path))
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("DSH_MODEL", raising=False)
    from finana.config import Settings

    s = Settings()
    assert s.deepseek_api_key == ""
    assert s.dsh_model == "deepseek-v4-flash"
    assert s.database_path == tmp_path / "finana.db"
    assert s.sessions_dir == tmp_path / "sessions"
    assert s.logs_dir == tmp_path / "logs"


def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("DSH_MODEL", "deepseek-v4-pro")
    from finana.config import Settings

    s = Settings()
    assert s.deepseek_api_key == "sk-test"
    assert s.dsh_model == "deepseek-v4-pro"


def test_get_settings_cached(monkeypatch, tmp_path):
    monkeypatch.setenv("FINANA_HOME", str(tmp_path))
    from finana.config import get_settings

    assert get_settings() is get_settings()
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/v2/test_config.py -v`
Expected: FAIL（ModuleNotFoundError: finana）

- [ ] **Step 3: 实现**

```bash
mkdir -p finana/storage finana/datacore/providers finana/memory finana/goals finana/prediction finana/prompts finana/web tests/v2
touch finana/__init__.py finana/storage/__init__.py finana/datacore/__init__.py finana/datacore/providers/__init__.py finana/memory/__init__.py finana/goals/__init__.py finana/prediction/__init__.py finana/web/__init__.py finana/py.typed
```

```python
# conftest.py（仓库根目录）
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
```

```python
# finana/config.py
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    deepseek_api_key: str = ""
    deepseek_base_url: str = ""
    dsh_model: str = "deepseek-v4-flash"
    finana_home: Path = Path.home() / ".finana"
    db_path: Path | None = None
    log_level: str = "INFO"
    http_timeout: int = 10

    @property
    def database_path(self) -> Path:
        return self.db_path or self.finana_home / "finana.db"

    @property
    def sessions_dir(self) -> Path:
        return self.finana_home / "sessions"

    @property
    def logs_dir(self) -> Path:
        return self.finana_home / "logs"

    def ensure_dirs(self) -> None:
        for d in (self.finana_home, self.sessions_dir, self.logs_dir, self.finana_home / "reports"):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`.env.example`：
```bash
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=
DSH_MODEL=deepseek-v4-flash
FINANA_HOME=~/.finana
```

`requirements.txt` 追加两行：
```
pydantic-settings>=2.0
fastmcp>=2.0
```

`requirements-dev.txt` 追加一行：
```
requests-mock>=1.12
```

然后安装：`pip install -r requirements-dev.txt -r requirements.txt`

- [ ] **Step 4: 运行测试通过**

Run: `python -m pytest tests/v2/test_config.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add finana/ conftest.py .env.example requirements.txt requirements-dev.txt tests/v2/test_config.py
git commit -m "feat: scaffold finana v2 package with settings"
```

---

### Task 2: SQLite 连接与 schema（metrics 表）

**Files:**
- Create: `finana/storage/schema.sql`、`finana/storage/db.py`
- Test: `tests/v2/test_db.py`

**Interfaces:**
- Consumes: `Settings.database_path`
- Produces: `finana.storage.db.connect(path: Path) -> sqlite3.Connection`、`finana.storage.db.get_db() -> sqlite3.Connection`（进程单例）。Plan 2/3 向 `schema.sql` 追加表即可被自动执行。

- [ ] **Step 1: 写失败测试**

```python
# tests/v2/test_db.py
import sqlite3


def test_connect_wal_and_schema(tmp_path):
    from finana.storage.db import connect

    conn = connect(tmp_path / "t.db")
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode == "wal"
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"metrics", "kv"} <= tables


def test_connect_idempotent(tmp_path):
    from finana.storage.db import connect

    connect(tmp_path / "t.db")
    conn = connect(tmp_path / "t.db")
    assert isinstance(conn, sqlite3.Connection)


def test_get_db_singleton(monkeypatch, tmp_path):
    monkeypatch.setenv("FINANA_HOME", str(tmp_path))
    from finana.storage import db

    db._conn = None
    assert db.get_db() is db.get_db()
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/v2/test_db.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现**

`finana/storage/schema.sql`：
```sql
CREATE TABLE IF NOT EXISTS kv (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at REAL NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS metrics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  name TEXT NOT NULL,
  value REAL NOT NULL,
  tags_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_metrics_name_ts ON metrics(name, ts);
```

`finana/storage/db.py`：
```python
import sqlite3
from pathlib import Path

_conn: sqlite3.Connection | None = None

_SCHEMA = Path(__file__).parent / "schema.sql"


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_SCHEMA.read_text(encoding="utf-8"))
    return conn


def get_db():
    global _conn
    if _conn is None:
        from finana.config import get_settings

        _conn = connect(get_settings().database_path)
    return _conn
```

- [ ] **Step 4: 运行测试通过**

Run: `python -m pytest tests/v2/test_db.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add finana/storage/ tests/v2/test_db.py
git commit -m "feat: add sqlite connection and base schema"
```

---

### Task 3: 日志与指标（observability）

**Files:**
- Create: `finana/observability.py`
- Test: `tests/v2/test_observability.py`

**Interfaces:**
- Consumes: `storage.db.get_db`（metrics 表）、`Settings.logs_dir/log_level`
- Produces:
  - `get_logger(name: str) -> logging.Logger`（JSON Lines 到文件 + 控制台简洁格式）
  - `run_trace(tid: str | None = None)` 上下文管理器，yield `trace_id: str`
  - `current_trace_id() -> str`
  - `MetricsService(conn)`：`record(name: str, value: float = 1, **tags)`、`summary(name: str, since: float) -> dict`（count/avg/p50/p95）
  - `get_metrics() -> MetricsService`（单例）

- [ ] **Step 1: 写失败测试**

```python
# tests/v2/test_observability.py
import json
import logging
import time


def test_trace_context(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANA_HOME", str(tmp_path))
    from finana import observability as obs
    from finana.config import Settings

    obs.init_logging(Settings())
    with obs.run_trace() as tid:
        assert len(tid) == 32
        assert obs.current_trace_id() == tid
        rec = {"tid": obs.current_trace_id()}
    assert rec["tid"] == tid


def test_logger_writes_json_with_trace(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANA_HOME", str(tmp_path))
    from finana import observability as obs
    from finana.config import Settings

    s = Settings()
    s.ensure_dirs()
    obs.init_logging(s, force=True)
    with obs.run_trace():
        logging.getLogger("finana.test").info("hello %s", "world")
    log_file = s.logs_dir / "finana.log"
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    entry = json.loads(lines[-1])
    assert entry["message"] == "hello world"
    assert len(entry["trace_id"]) == 32
    assert entry["level"] == "INFO"


def test_metrics_record_and_summary(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANA_HOME", str(tmp_path))
    from finana import observability as obs
    from finana.storage.db import get_db

    m = obs.MetricsService(get_db())
    for i, v in enumerate([10, 20, 30, 40]):
        m.record("analysis.latency_ms", v, stage="harness")
        time.sleep(0.001)
    s = m.summary("analysis.latency_ms", since=time.time() - 60)
    assert s["count"] == 4
    assert s["avg"] == 25
    assert s["p50"] == 20
    assert s["max"] == 40
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/v2/test_observability.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
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
    return _trace_id.get()


@contextmanager
def run_trace(tid: str | None = None):
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
    return logging.getLogger(f"finana.{name}")


class MetricsService:
    def __init__(self, conn):
        self.conn = conn

    def record(self, name: str, value: float = 1, **tags):
        self.conn.execute(
            "INSERT INTO metrics(ts,name,value,tags_json) VALUES(?,?,?,?)",
            (time.time(), name, float(value), json.dumps(tags, ensure_ascii=False)),
        )
        self.conn.commit()

    def summary(self, name: str, since: float) -> dict:
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
            "max": max(vals),
        }


_metrics = None


def get_metrics() -> MetricsService:
    global _metrics
    if _metrics is None:
        from finana.storage.db import get_db

        _metrics = MetricsService(get_db())
    return _metrics
```

- [ ] **Step 4: 运行测试通过**

Run: `python -m pytest tests/v2/test_observability.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add finana/observability.py tests/v2/test_observability.py
git commit -m "feat: add structured logging and sqlite metrics"
```

---

### Task 4: datacore 数据模型与 symbol 规范化

**Files:**
- Create: `finana/datacore/models.py`、`finana/datacore/symbols.py`
- Test: `tests/v2/test_symbols.py`、`tests/v2/test_models.py`

**Interfaces:**
- Produces（Plan 1 后续任务与 Plan 2 MCP 工具共同依赖）:
  - `normalize_symbol(raw: str) -> str`，输出规范形 `"600519.SH" | "000001.SZ" | "430047.BJ"`；纯 6 位数字按首位规则猜交易所（6/9→SH，0/2/3→SZ，4/8→BJ）；指数必须显式带前缀或后缀（如 `sh000001`→`000001.SH`，但裸 `000001` 是平安银行不是上证指数）
  - `to_em_secid(sym: str) -> str`（`600519.SH`→`1.600519`）、`to_sina_code(sym)`（→`sh600519`）、`to_tencent_code(sym)`（→`sh600519`）
  - dataclasses：`Bar(date,open_,high,low,close,volume,amount)`、`KLine(symbol,period,bars:list[Bar],source)`、`Quote(symbol,name,price,change_pct,open_,high,low,prev_close,volume,amount,timestamp,source)`、`MoneyFlowDay(date,main_net,source)`；news/financials 用 `list[dict]`/`dict`

- [ ] **Step 1: 写失败测试**

```python
# tests/v2/test_symbols.py
import pytest

from finana.datacore.symbols import normalize_symbol, to_em_secid, to_sina_code


@pytest.mark.parametrize("raw,expected", [
    ("600519", "600519.SH"),
    ("sh600519", "600519.SH"),
    ("600519.SH", "600519.SH"),
    ("000001", "000001.SZ"),
    ("sz000001", "000001.SZ"),
    ("300750", "300750.SZ"),
    ("688981", "688981.SH"),
    ("sh000001", "000001.SH"),
    ("430047", "430047.BJ"),
])
def test_normalize(raw, expected):
    assert normalize_symbol(raw) == expected


def test_normalize_index_vs_stock():
    assert normalize_symbol("000001.SZ") != normalize_symbol("000001.SH")


def test_secid_mapping():
    assert to_em_secid("600519.SH") == "1.600519"
    assert to_em_secid("000001.SZ") == "0.000001"


def test_sina_code():
    assert to_sina_code("600519.SH") == "sh600519"
    assert to_sina_code("000001.SZ") == "sz000001"
```

```python
# tests/v2/test_models.py
from finana.datacore.models import Bar, KLine, Quote


def test_bar_holds_values():
    b = Bar("2026-08-25", 10.0, 11.0, 9.8, 10.5, 12345, 1.3e8)
    assert b.close == 10.5


def test_kline_defaults():
    k = KLine(symbol="600519.SH", period="d", bars=[], source="test")
    assert k.period == "d" and k.bars == []
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/v2/test_symbols.py tests/v2/test_models.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# finana/datacore/symbols.py
_SH_PREFIXES = ("60", "68", "9")
_SZ_PREFIXES = ("00", "30", "20")
_BJ_PREFIXES = ("43", "83", "87", "88", "92")


def _suffix_for(code: str) -> str:
    if code.startswith(_SH_PREFIXES):
        return ".SH"
    if code.startswith(_BJ_PREFIXES):
        return ".BJ"
    return ".SZ"


def normalize_symbol(raw: str) -> str:
    s = raw.strip().upper().replace(".", "")
    for pfx in ("SH", "SZ", "BJ"):
        if s.startswith(pfx) and len(s) > len(pfx):
            return s[len(pfx):] + "." + pfx
    if s.endswith(("SH", "SZ", "BJ")) and s[:-2].isdigit():
        return s[:-2] + "." + s[-2:]
    if s.isdigit() and len(s) == 6:
        return s + _suffix_for(s)
    raise ValueError(f"无法识别的股票代码: {raw!r}")


def to_em_secid(sym: str) -> str:
    code, _, mkt = sym.partition(".")
    return ("1." if mkt == "SH" else "0.") + code


def to_sina_code(sym: str) -> str:
    code, _, mkt = sym.partition(".")
    return mkt.lower() + code


to_tencent_code = to_sina_code
```

```python
# finana/datacore/models.py
from dataclasses import dataclass, field


@dataclass
class Bar:
    date: str
    open_: float
    high: float
    low: float
    close: float
    volume: float
    amount: float = 0.0


@dataclass
class KLine:
    symbol: str
    period: str
    bars: list[Bar] = field(default_factory=list)
    source: str = ""


@dataclass
class Quote:
    symbol: str
    name: str
    price: float
    change_pct: float
    open_: float
    high: float
    low: float
    prev_close: float
    volume: float
    amount: float
    timestamp: float
    source: str = ""


@dataclass
class MoneyFlowDay:
    date: str
    main_net: float
    source: str = ""
```

- [ ] **Step 4: 运行测试通过**

Run: `python -m pytest tests/v2/test_symbols.py tests/v2/test_models.py -v`
Expected: 全部 passed

- [ ] **Step 5: Commit**

```bash
git add finana/datacore/ tests/v2/test_symbols.py tests/v2/test_models.py
git commit -m "feat: add datacore models and symbol normalization"
```

---

### Task 5: 熔断器、TTL 缓存与域路由

**Files:**
- Create: `finana/datacore/base.py`
- Test: `tests/v2/test_breaker.py`、`tests/v2/test_router.py`

**Interfaces:**
- Consumes: Task 3 的 `get_metrics`、`get_logger`
- Produces:
  - `CircuitBreaker(threshold=3, cooldown=300.0, time_func=time.monotonic)`：`allow() -> bool`、`record_success()`、`record_failure()`、`state -> str`（closed/open/half-open）
  - `TTLCache(default_ttl=60.0, time_func=time.monotonic)`：`get(key)`、`put(key, value, ttl=None)`
  - `DataUnavailable(Exception)`，字段 `domain, attempts: list[str]`
  - `DomainRouter`：`register(domain: str, provider)`（provider 有 `name` 属性与同名方法）、`dispatch(domain: str, method: str, *args, cache_ttl: float | None = None)`——按注册顺序尝试可用渠道，全部失败抛 `DataUnavailable`；成功结果写入缓存并记 metric `{domain}.{provider}.latency_ms`

- [ ] **Step 1: 写失败测试**

```python
# tests/v2/test_breaker.py


def test_breaker_opens_after_threshold():
    from finana.datacore.base import CircuitBreaker

    clock = [0.0]
    br = CircuitBreaker(threshold=3, cooldown=300, time_func=lambda: clock[0])
    for _ in range(3):
        assert br.allow()
        br.record_failure()
    assert br.state == "open"
    assert not br.allow()


def test_breaker_half_open_then_close():
    from finana.datacore.base import CircuitBreaker

    clock = [0.0]
    br = CircuitBreaker(threshold=2, cooldown=10, time_func=lambda: clock[0])
    for _ in range(2):
        br.record_failure()
    clock[0] = 11.0
    assert br.state == "half-open"
    assert br.allow()
    br.record_success()
    assert br.state == "closed"


def test_breaker_reopens_on_half_open_failure():
    from finana.datacore.base import CircuitBreaker

    clock = [0.0]
    br = CircuitBreaker(threshold=1, cooldown=10, time_func=lambda: clock[0])
    br.record_failure()
    clock[0] = 11.0
    br.allow()
    br.record_failure()
    assert br.state == "open" and not br.allow()
```

```python
# tests/v2/test_router.py
import pytest

from finana.datacore.base import DataUnavailable, DomainRouter, TTLCache


class Ok:
    name = "ok"

    def get_x(self, v):
        return v * 2


class Bad:
    name = "bad"
    fails = 99

    def get_x(self, v):
        raise RuntimeError("boom")


def test_ttl_cache_expiry():
    clock = [0.0]
    c = TTLCache(time_func=lambda: clock[0])
    c.put("k", 1, ttl=10)
    assert c.get("k") == 1
    clock[0] += 11
    assert c.get("k") is None


def test_router_success_first_provider():
    r = DomainRouter()
    r.register("x", Ok())
    assert r.dispatch("x", "get_x", 21, cache_ttl=None) == 42


def test_router_failover_to_next():
    bad, ok = Bad(), Ok()
    r = DomainRouter()
    r.register("x", bad)
    r.register("x", ok)
    assert r.dispatch("x", "get_x", 5) == 10


def test_router_all_fail_raises():
    r = DomainRouter()
    r.register("x", Bad())
    with pytest.raises(DataUnavailable) as ei:
        r.dispatch("x", "get_x", 1)
    assert "bad" in ei.value.attempts


def test_router_skips_open_breaker():
    bad = Bad()
    r = DomainRouter()
    r.register("x", bad)
    r.register("x", Ok())
    for _ in range(3):
        r.dispatch("x", "get_x", 1)
    assert bad.fails == 3
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/v2/test_breaker.py tests/v2/test_router.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# finana/datacore/base.py
import time
from collections import OrderedDict

from finana.observability import get_logger, get_metrics

log = get_logger("datacore")


class DataUnavailable(Exception):
    def __init__(self, domain: str, attempts: list[str]):
        self.domain = domain
        self.attempts = attempts
        super().__init__(f"{domain} 所有渠道失败: {attempts}")


class CircuitBreaker:
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
        if self.failures < self.threshold:
            return "closed"
        if self.time_func() - self.opened_at >= self.cooldown:
            return "half-open"
        return "open"

    def allow(self) -> bool:
        return self.state != "open"

    def record_success(self):
        self.failures = 0

    def record_failure(self, err: Exception):
        self.failures += 1
        self.last_error = f"{type(err).__name__}: {err}"
        self.last_error_at = self.time_func()
        if self.failures >= self.threshold:
            self.opened_at = self.time_func()


class TTLCache:
    def __init__(self, default_ttl: float = 60.0, time_func=time.monotonic, max_items: int = 512):
        self.default_ttl = default_ttl
        self.time_func = time_func
        self.max_items = max_items
        self._store: OrderedDict = OrderedDict()

    def put(self, key, value, ttl: float | None = None):
        self._store[key] = (self.time_func() + (ttl or self.default_ttl), value)
        self._store.move_to_end(key)
        while len(self._store) > self.max_items:
            self._store.popitem(last=False)

    def get(self, key):
        item = self._store.get(key)
        if not item:
            return None
        exp, val = item
        if self.time_func() >= exp:
            del self._store[key]
            return None
        return val


class DomainRouter:
    def __init__(self):
        self._domains: dict[str, list] = {}
        self._breakers: dict[tuple, CircuitBreaker] = {}

    def register(self, domain: str, provider):
        self._domains.setdefault(domain, []).append(provider)

    def _breaker(self, key: tuple) -> CircuitBreaker:
        if key not in self._breakers:
            self._breakers[key] = CircuitBreaker()
        return self._breakers[key]

    def chain(self, domain: str) -> list:
        return self._domains.get(domain, [])

    def dispatch(self, domain: str, method: str, *args, cache: TTLCache | None = None, cache_ttl: float | None = None):
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
```

- [ ] **Step 4: 运行测试通过**

Run: `python -m pytest tests/v2/test_breaker.py tests/v2/test_router.py -v`
Expected: 全部 passed

- [ ] **Step 5: Commit**

```bash
git add finana/datacore/base.py tests/v2/test_breaker.py tests/v2/test_router.py
git commit -m "feat: add circuit breaker, ttl cache, domain router"
```

---

### Task 6: 东方财富 provider（行情/K线/搜索解析 + 资金/财务/新闻/板块）

**Files:**
- Create: `finana/datacore/providers/em.py`、`finana/datacore/http.py`
- Test: `tests/v2/em_fixtures/`（录制的响应样本）、`tests/v2/test_em_provider.py`

**Interfaces:**
- Consumes: models/symbols（Task 4）、`http.py` 提供 `fetch_json(url, params=None, headers=None, timeout=10) -> dict`（requests 封装，统一 UA 与超时，供所有 provider 复用）
- Produces: `EastmoneyProvider` 实例方法：`get_quote(sym: str) -> Quote`、`get_kline(sym: str, period: str = "d", count: int = 120) -> KLine`、`resolve(query: str) -> list[dict]`（返回 `[{"symbol","code","name","market"}...]`）、`get_money_flow(sym, days=10) -> list[MoneyFlowDay]`、`get_margin(sym, days=20) -> list[dict]`、`get_lhb(sym, days=30) -> list[dict]`、`get_financials(sym) -> dict`、`get_news(sym, limit=10) -> list[dict]`、`get_sector_snapshot(limit=50) -> list[dict]`。`name = "eastmoney"`

**已知端点（Task 11 spike 校准对象）**：行情 `push2.eastmoney.com/api/qt/stock/get`（secid 前缀 SH=1/SZ=0，价格按 `f59` 位小数缩放，缺省 ÷100）；K线 `push2his.../stock/kline/get`（klt 101/102/103=日周月，fqt=1 前复权，klines 为逗号串数组）；资金流 `push2.../stock/fflow/daykline/get`；两融 `datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPTA_WEB_RZRQ_GGMX`；龙虎榜 `RPT_DAILYBILLBOARD_DETAILSNEW`；财务 `emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/MainTargetAjaxNew`；搜索 `searchapi.eastmoney.com/api/suggest/get`；板块 `push2.../clist/get?fs=m:90+t:2`。

- [ ] **Step 1: 录制/构造 fixture 并写失败测试**

用 requests-mock 拦截 URL 回放 fixture。fixture 文件放 `tests/v2/em_fixtures/`：`quote_600519.json`（含 f57 名称、f43 价格×10^f59、f60 昨收等最小字段集 f43,f44,f45,f46,f47,f48,f57,f58,f59,f60,f86）、`kline_600519.json`（klines 数组 ≥3 条）、`suggest_maotai.json`、`fflow.json`、`margin.json`、`lhb.json`、`f10.json`、`news.json`、`sector.json`（各含 2 条样例记录，结构按上述端点真实返回裁剪）。

```python
# tests/v2/test_em_provider.py
import json
from pathlib import Path

import pytest
import requests_mock as rm_module

FIXTURES = Path(__file__).parent / "em_fixtures"


def _load(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def em():
    from finana.datacore.providers.em import EastmoneyProvider

    return EastmoneyProvider()


def test_get_quote(em, requests_mock):
    requests_mock.get(rm_module.ANY, text=_load("quote_600519.json"))
    q = em.get_quote("600519.SH")
    assert q.symbol == "600519.SH"
    assert abs(q.price - 1525.6) < 0.01
    assert q.change_pct == pytest.approx(1.23, abs=0.01)
    assert q.source == "eastmoney"


def test_get_kline(em, requests_mock):
    requests_mock.get(rm_module.ANY, text=_load("kline_600519.json"))
    k = em.get_kline("600519.SH", period="d", count=3)
    assert k.source == "eastmoney"
    assert len(k.bars) == 3
    assert k.bars[-1].close > 0


def test_resolve(em, requests_mock):
    requests_mock.get(rm_module.ANY, text=_load("suggest_maotai.json"))
    out = em.resolve("茅台")
    assert out and out[0]["name"].startswith("贵州茅台")


def test_money_flow_parses(em, requests_mock):
    requests_mock.get(rm_module.ANY, text=_load("fflow.json"))
    days = em.get_money_flow("600519.SH", days=2)
    assert len(days) == 2 and days[0].main_net != 0
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/v2/test_em_provider.py -v`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现**

```python
# finana/datacore/http.py
import requests

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"


def fetch_json(url, params=None, headers=None, timeout: int = 10) -> dict:
    h = {"User-Agent": _UA}
    if headers:
        h.update(headers)
    resp = requests.get(url, params=params, headers=h, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def fetch_text(url, params=None, headers=None, timeout: int = 10) -> str:
    h = {"User-Agent": _UA}
    if headers:
        h.update(headers)
    resp = requests.get(url, params=params, headers=h, timeout=timeout)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "gbk"
    return resp.text
```

`finana/datacore/providers/em.py`（核心解析逻辑完整给出，其余方法同构）：

```python
import json
import time

from finana.datacore.http import fetch_json
from finana.datacore.models import Bar, KLine, MoneyFlowDay, Quote
from finana.datacore.symbols import to_em_secid

PUSH2 = "https://push2.eastmoney.com/api/qt/stock/get"
PUSH2_KLINE = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
PUSH2_FFLOW = "https://push2.eastmoney.com/api/qt/stock/fflow/daykline/get"
DATACENTER = "https://datacenter-web.eastmoney.com/api/data/v1/get"
F10 = "https://emweb.securities.eastmoney.com/PC_HSF10/NewFinanceAnalysis/MainTargetAjaxNew"
SUGGEST = "https://searchapi.eastmoney.com/api/suggest/get"
CLIST = "https://push2.eastmoney.com/api/qt/clist/get"
KLT = {"d": 101, "w": 102, "m": 103}


class EastmoneyProvider:
    name = "eastmoney"

    def _scaled(self, raw: float | None, digits_field, data: dict) -> float:
        if raw is None:
            return 0.0
        return raw / (10 ** data.get(digits_field, 2))

    def get_quote(self, sym: str) -> Quote:
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
        data = fetch_json(SUGGEST, params={"input": query, "type": "14", "count": 5})
        out = []
        for item in (data.get("QuotationCodeTable", {}).get("Data") or []):
            out.append({
                "code": item.get("Code"), "name": item.get("Name"),
                "market": item.get("MktNum"), "symbol": f"{item.get('Code')}",
            })
        return out

    def get_money_flow(self, sym: str, days: int = 10) -> list[MoneyFlowDay]:
        data = fetch_json(PUSH2_FFLOW, params={
            "secid": to_em_secid(sym), "klt": 101, "lmt": days,
            "fields1": "f1,f2,f3,f7", "fields2": "f51,f52",
        })["data"]
        return [MoneyFlowDay(date=r.split(",")[0], main_net=float(r.split(",")[1]), source=self.name)
                for r in data.get("klines", [])]

    def get_margin(self, sym: str, days: int = 20) -> list[dict]:
        code = sym.split(".")[0]
        data = fetch_json(DATACENTER, params={
            "reportName": "RPTA_WEB_RZRQ_GGMX", "columns": "ALL",
            "filter": f'(scode="{code}")', "sortColumns": "dim_date",
            "sortTypes": "-1", "pageSize": days,
        })
        return (data.get("result") or {}).get("data") or []

    def get_lhb(self, sym: str, days: int = 30) -> list[dict]:
        code = sym.split(".")[0]
        data = fetch_json(DATACENTER, params={
            "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW", "columns": "ALL",
            "filter": f'(SECURITY_CODE="{code}")', "sortColumns": "TRADE_DATE",
            "sortTypes": "-1", "pageSize": days,
        })
        return (data.get("result") or {}).get("data") or []

    def get_financials(self, sym: str) -> dict:
        data = fetch_json(F10, params={"type": "0", "code": sym.replace(".", "")})
        rows = data if isinstance(data, list) else data.get("data", [])
        return rows[0] if rows else {}

    def get_news(self, sym: str, limit: int = 10) -> list[dict]:
        code = sym.split(".")[0]
        data = fetch_json(
            "https://search-api-web.eastmoney.com/search/jsonp",
            params={"cb": "", "param": json.dumps({
                "uid": "", "keyword": code, "type": ["cmsArticleWebOld"], "client": "web",
                "clientVersion": "curr",
                "param": {"cmsArticleWebOld": {"searchScope": "default", "sort": "default",
                                               "pageIndex": 1, "pageSize": limit}},
            })},
        )
        arts = (data.get("result", {}).get("cmsArticleWebOld") or [])
        return [{"title": a.get("title", "").replace("<em>", "").replace("</em>", ""),
                 "date": a.get("date"), "url": a.get("url")} for a in arts]

    def get_sector_snapshot(self, limit: int = 50) -> list[dict]:
        data = fetch_json(CLIST, params={
            "pn": 1, "pz": limit, "po": 1, "np": 1, "fltt": 2, "fid": "f3",
            "fs": "m:90 t:2", "fields": "f2,f3,f12,f14",
        })
        return [{"code": d.get("f12"), "name": d.get("f14"), "change_pct": d.get("f3")}
                for d in (data.get("data", {}) or {}).get("diff", [])]
```

注意：fixture 内容按上面字段契约手工构造真实形状（如 quote fixture：`{"rc":0,"data":{"f57":"600519","f58":"贵州茅台","f43":152560,"f59":2,"f44":153200,"f45":151800,"f46":151500,"f47":23456,"f48":3567000000,"f60":150700,"f86":1756051200}}`，使 price=1525.60、prev=1507.00→change_pct≈1.23；klines 样例三条 `"2026-08-21,1500.00,1510.00,1520.00,1495.00,20000,3020000000"` 等）。

- [ ] **Step 4: 运行测试通过**

Run: `python -m pytest tests/v2/test_em_provider.py -v`
Expected: 全部 passed（fixture 与解析契约一致）

- [ ] **Step 5: Commit**

```bash
git add finana/datacore/ tests/v2/
git commit -m "feat: add eastmoney provider with fixtures"
```

---

### Task 7: 新浪/腾讯 provider（备用渠道）

**Files:**
- Create: `finana/datacore/providers/sina_tencent.py`
- Test: `tests/v2/test_sina_tencent.py`

**Interfaces:**
- Consumes: `http.fetch_text`、symbols/models
- Produces: `SinaTencentProvider`（`name="sina_tencent"`）：`get_quote(sym) -> Quote`（新浪主取，腾讯兜底在同一方法内二级 try）、`get_kline(sym, period="d", count=120) -> KLine`（腾讯 `web.ifzq.gtimg.cn/appstock/app/fqkline/get`，qfq）。仅实现这两个域（注册时只挂 quote/kline）。

新浪行情：`https://hq.sinajs.cn/list=sh600519`（**path 式**，非 query 参数），Header 必须 `Referer: https://finance.sina.com.cn`；GBK 解码；字段 `名称,今开,昨收,现价,最高,最低,...,成交量(股),成交额(元),...`。
腾讯行情：`https://qt.gtimg.cn/q=sh600519` GBK，`~` 分隔：1名称 3现价 4昨收 5今开 33最高 34最低 36成交量(手) 37成交额(万)。
腾讯K线 JSON：`https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},{freq},,,{count},qfq`，`data[code].qfqday`（或 `{freq}`）数组 `[date,open,close,high,low,volume]`。

- [ ] **Step 1: 写失败测试**

```python
# tests/v2/test_sina_tencent.py
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
                           '0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~'
                           '1532.00~1518.00~0~23456~35670~'
                           '0~0~0~0~0~0~0~0~0~0~0~0~0~0~0";')
    q = SinaTencentProvider().get_quote("600519.SH")
    assert q.price == 1525.6
    assert q.source.endswith("_tx")


def test_kline_from_tencent(requests_mock):
    from finana.datacore.providers.sina_tencent import SinaTencentProvider

    body = '{"code":0,"msg":"","data":{"sh600519":{"qfqday":[["2026-08-23","1500.00","1510.00","1520.00","1495.00","20000.00"],["2026-08-24","1510.00","1515.00","1525.00","1505.00","21000.00"],["2026-08-25","1515.00","1525.60","1532.00","1510.00","23456.00"]]}}}'
    requests_mock.get(TX_KLINE_URL, text=body)
    k = SinaTencentProvider().get_kline("600519.SH", period="d", count=3)
    assert len(k.bars) == 3 and k.bars[-1].close == 1525.6
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/v2/test_sina_tencent.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# finana/datacore/providers/sina_tencent.py
import json
import time

from finana.datacore.http import fetch_text
from finana.datacore.models import Bar, KLine, Quote
from finana.datacore.symbols import to_sina_code

SINA_HEADERS = {"Referer": "https://finance.sina.com.cn"}
TX_KLINE_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"


class SinaTencentProvider:
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
        try:
            return self._sina_quote(sym)
        except Exception:
            return self._tx_quote(sym)

    def get_kline(self, sym: str, period: str = "d", count: int = 120) -> KLine:
        freq = {"d": "day", "w": "week", "m": "month"}.get(period, "day")
        raw = fetch_text(TX_KLINE_URL, params={"param": f"{to_sina_code(sym)},{freq},,,{count},qfq"})
        node = json.loads(raw)["data"][to_sina_code(sym)]
        rows = node.get("qfqday") or node.get(freq) or []
        bars = [Bar(r[0], float(r[1]), float(r[3]), float(r[4]), float(r[2]),
                    float(r[5]), 0.0) for r in rows]
        return KLine(symbol=sym, period=period, bars=bars[-count:], source=self.name)
```

- [ ] **Step 4: 运行测试通过**

Run: `python -m pytest tests/v2/test_sina_tencent.py -v`
Expected: 全部 passed

- [ ] **Step 5: Commit**

```bash
git add finana/datacore/providers/sina_tencent.py tests/v2/test_sina_tencent.py
git commit -m "feat: add sina/tencent fallback provider"
```

---

### Task 8: 可选渠道 provider（AKShare、AllTick）

**Files:**
- Create: `finana/datacore/providers/akshare_p.py`、`finana/datacore/providers/alltick.py`
- Test: `tests/v2/test_optional_providers.py`

**Interfaces:**
- Produces: `AkshareProvider`（`name="akshare"`，仅 `get_kline`，经 `ak.stock_zh_a_hist(symbol=六位码, period="daily", count 经 start/end 控制, adjust="qfq")`；akshare 未安装时构造抛 `ImportError` 由组装方跳过）；`AlltickProvider`（`name="alltick"`，仅 `get_quote`，需 `settings.alltick_token`，未配置则组装方跳过；GET `https://quote.alltick.co/quote-stock/v2/query?code={code}.{SH|SZ}&token=...` 解析 `data[*].last_price`，字段名以 spike 实测为准并在本任务内修正）。
- Modify: `finana/config.py` 增加 `alltick_token: str = ""`

- [ ] **Step 1: 写失败测试**

```python
# tests/v2/test_optional_providers.py
import pandas as pd
import pytest


class FakeAk:
    @staticmethod
    def stock_zh_a_hist(symbol, period, start_date, end_date, adjust):
        return pd.DataFrame({
            "日期": ["2026-08-24", "2026-08-25"],
            "开盘": [1500.0, 1515.0], "收盘": [1510.0, 1525.6],
            "最高": [1520.0, 1532.0], "最低": [1495.0, 1510.0],
            "成交量": [20000, 23456], "成交额": [3.02e9, 3.57e9],
        })


def test_akshare_kline(monkeypatch):
    import finana.datacore.providers.akshare_p as mod

    monkeypatch.setattr(mod, "_ak", FakeAk)
    p = mod.AkshareProvider()
    k = p.get_kline("600519.SH", period="d", count=2)
    assert k.source == "akshare" and len(k.bars) == 2 and k.bars[-1].close == 1525.6


def test_alltick_quote(requests_mock):
    from finana.datacore.providers.alltick import AlltickProvider

    requests_mock.get("https://quote.alltick.co/quote-stock/v2/query", json={
        "data": [{"code": "600519.SH", "last_price": 1525.6, "prev_closed": 1507.0}]})
    p = AlltickProvider(token="tok")
    q = p.get_quote("600519.SH")
    assert q.price == 1525.6
    assert q.source == "alltick"
    assert q.change_pct == pytest.approx(1.23, abs=0.01)
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/v2/test_optional_providers.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

```python
# finana/datacore/providers/akshare_p.py
import time
from datetime import date, timedelta

from finana.datacore.models import Bar, KLine

try:
    import akshare as _ak
except ImportError:
    _ak = None

_PERIOD_MAP = {"d": "daily", "w": "weekly", "m": "monthly"}


class AkshareProvider:
    name = "akshare"

    def __init__(self):
        if _ak is None:
            raise ImportError("akshare 未安装: pip install akshare")

    def get_kline(self, sym: str, period: str = "d", count: int = 120) -> KLine:
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
```

```python
# finana/datacore/providers/alltick.py
import time

from finana.datacore.http import fetch_json
from finana.datacore.models import Quote

QUERY_URL = "https://quote.alltick.co/quote-stock/v2/query"


class AlltickProvider:
    name = "alltick"

    def __init__(self, token: str):
        if not token:
            raise ImportError("alltick token 未配置(FINANA_ALLTICK_TOKEN)")
        self.token = token

    def get_quote(self, sym: str) -> Quote:
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
```

`finana/config.py` 的 `Settings` 内追加字段：

```python
    alltick_token: str = ""
```

注意：AllTick 免费档字段名以 Task 11 实测为准；若实测返回结构与上述解析不符，在本任务文件内修正并同步更新测试。

- [ ] **Step 4: 运行测试通过**

Run: `python -m pytest tests/v2/test_optional_providers.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add finana/datacore/providers/ finana/config.py tests/v2/test_optional_providers.py
git commit -m "feat: add optional akshare and alltick providers"
```

---

### Task 9: DataCore 门面（默认优先级 + health 报告）

**Files:**
- Create: `finana/datacore/core.py`、`finana/datacore/registry.py`
- Test: `tests/v2/test_core.py`

**Interfaces:**
- Consumes: Task 5 Router/Cache、Tasks 6-8 providers
- Produces:
  - `registry.build_providers(settings) -> list`：按 `settings.provider_order`（逗号分隔字符串，默认 `"eastmoney,sina_tencent,akshare,alltick"`）实例化，跳过不可用者（akshare 未安装、alltick 无 token），返回实例列表
  - `DataCore(settings)`：属性 `quote/kline/moneyflow/margin/lhb/financials/news/sector` 各自是独立 `DomainRouter`；公开方法即 spec §4.2 的八个数据函数（签名同 provider 方法，首参 symbol 先 `normalize_symbol`）；内部 `self.cache = TTLCache(default_ttl=60)`；TTL 策略：quote 30s、kline 300s、moneyflow 300s、其余 1800s；`health() -> list[dict]`（每 provider×domain 输出 `{provider,domain,state,failures,last_error,last_error_at}`）
  - `get_datacore() -> DataCore`（单例）

- [ ] **Step 1: 写失败测试**

```python
# tests/v2/test_core.py
import pytest

from finana.datacore.base import CircuitBreaker, DataUnavailable


class StubP:
    def __init__(self, name, fail=False):
        self.name, self.fail = name, fail
        self.calls = 0

    def get_quote(self, sym):
        self.calls += 1
        if self.fail:
            raise RuntimeError("down")
        from finana.datacore.models import Quote

        return Quote(sym, "stub", 1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0.0, source=self.name)

    def get_kline(self, sym, period="d", count=10):
        from finana.datacore.models import KLine

        return KLine(sym, period, [], source=self.name)


def _make_core(first, second):
    from finana.datacore.core import DataCore

    core = DataCore.__new__(DataCore)
    from finana.datacore.base import DomainRouter, TTLCache

    core.cache = TTLCache(default_ttl=60)
    quote_r, kline_r = DomainRouter(), DomainRouter()
    for p in (first, second):
        if hasattr(p, "get_quote"):
            quote_r.register("quote", p)
        if hasattr(p, "get_kline"):
            kline_r.register("kline", p)
    core._routers = {"quote": quote_r, "kline": kline_r}
    return core


def test_normalize_inside_facade():
    core = _make_core(StubP("a"), StubP("b"))
    q = core.get_quote("600519")
    assert q.symbol == "600519.SH"


def test_failover_and_caching():
    dead, alive = StubP("dead", fail=True), StubP("live")
    core = _make_core(dead, alive)
    q1 = core.get_quote("600519.SH")
    q2 = core.get_quote("600519.SH")
    assert q1.source == "live"
    assert alive.calls == 1
    assert dead.calls == 1


def test_health_reports_states():
    core = _make_core(StubP("a"), StubP("b", fail=True))
    core.get_kline("600519.SH")
    states = {(h["provider"], h["domain"]) for h in core.health()}
    assert any(d == "kline" for _, d in states)


def test_unavailable_when_empty_chain():
    core = _make_core(StubP("a"), StubP("b"))
    core._routers["quote"]._domains["quote"] = []
    with pytest.raises(DataUnavailable):
        core.get_quote("600519.SH")
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/v2/test_core.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

`registry.py`：

```python
from finana.datacore.providers.em import EastmoneyProvider
from finana.datacore.providers.sina_tencent import SinaTencentProvider

_BUILDERS = {}


def register_builder(name, fn):
    _BUILDERS[name] = fn


register_builder("eastmoney", lambda s: EastmoneyProvider())
register_builder("sina_tencent", lambda s: SinaTencentProvider())


def _try_register_akshare():
    def build(settings):
        from finana.datacore.providers.akshare_p import AkshareProvider

        return AkshareProvider()
    try:
        import akshare  # noqa: F401
        register_builder("akshare", build)
    except ImportError:
        pass


_try_register_akshare()


def _try_register_alltick():
    def build(settings):
        if not settings.alltick_token:
            raise ImportError("alltick token 未配置")
        from finana.datacore.providers.alltick import AlltickProvider

        return AlltickProvider(token=settings.alltick_token)
    register_builder("alltick", build)


_try_register_alltick()


def build_providers(settings) -> list:
    order = [x.strip() for x in settings.provider_order.split(",") if x.strip()]
    out = []
    for name in order:
        builder = _BUILDERS.get(name)
        if not builder:
            continue
        try:
            out.append(builder(settings))
        except ImportError:
            continue
    return out
```

`core.py`：

```python
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

    def get_quote(self, symbol):
        return self._call("quote", "get_quote", symbol)

    def get_kline(self, symbol, period="d", count=120):
        return self._call("kline", "get_kline", symbol, period, count)

    def get_money_flow(self, symbol, days=10):
        return self._call("moneyflow", "get_money_flow", symbol, days)

    def get_margin(self, symbol, days=20):
        return self._call("margin", "get_margin", symbol, days)

    def get_lhb(self, symbol, days=30):
        return self._call("lhb", "get_lhb", symbol, days)

    def get_financials(self, symbol):
        return self._call("financials", "get_financials", symbol)

    def get_news(self, symbol, limit=10):
        return self._call("news", "get_news", symbol, limit)

    def get_sector_snapshot(self, limit=50):
        return self._call("sector", "get_sector_snapshot", limit, symbol_first=False)

    def health(self) -> list[dict]:
        out = []
        for domain, router in self._routers.items():
            for p in router.chain(domain):
                br = router._breakers.get((domain, p.name)) or CircuitBreakerView()
                out.append({"provider": p.name, "domain": domain, "state": br.state,
                            "failures": br.failures, "last_error": br.last_error})
        return out


class CircuitBreakerView:
    state, failures, last_error = "closed", 0, ""


@lru_cache
def get_datacore() -> DataCore:
    return DataCore()
```

（`health` 里 `router._breaker` 访问前需 `from finana.datacore.base import CircuitBreaker` 不必要，直接用 getattr 兜底即可——按上面 CircuitBreakerView 方式实现。）

- [ ] **Step 4: 运行测试通过 + 全量回归**

Run: `python -m pytest tests/v2/test_core.py -v && python -m pytest tests/v2/ -q`
Expected: 全部 passed

- [ ] **Step 5: Commit**

```bash
git add finana/datacore/ tests/v2/test_core.py
git commit -m "feat: assemble datacore facade with health reporting"
```

---

### Task 10: finana-doctor 渠道实测脚本

**Files:**
- Create: `finana/doctor.py`
- Test: `tests/v2/test_doctor.py`（用 stub DataCore）

**Interfaces:**
- Consumes: `get_datacore()` 各域方法、`DataUnavailable`、`core.health()`
- Produces: `python -m finana.doctor [--symbol 600519]`：对每个数据域发一次真实请求，输出域级结果表（状态/耗时/错误）+ 各渠道熔断状态表，并把快照 JSON 写到 `settings.finana_home/doctor_last.json`。无任何成功域时 exit 1。

- [ ] **Step 1: 写失败测试**

```python
# tests/v2/test_doctor.py
import pytest

from finana.datacore.base import CircuitBreaker, DataUnavailable


class RouterStub:
    def __init__(self, items=None):
        self.items = items or []

    def chain(self, _domain):
        return self.items

    def dispatch(self, domain, method, *args, **kwargs):
        if not self.items:
            raise DataUnavailable(domain, [f"{i}:skip" for i in []] or ["none"])
        return object()


def _stub_core():
    from finana.datacore.models import Quote

    class P:
        name = "p1"

        def get_quote(self, sym):
            return Quote(sym, "x", 1.0, 0.0, 1.0, 1.0, 1.0, 1.0, 0, 0, 0.0, source="p1")

    class Core:
        def __init__(self):
            self._routers = {
                "quote": RouterStub([P()]), "kline": RouterStub(),
                "moneyflow": RouterStub(), "margin": RouterStub(),
                "lhb": RouterStub(), "financials": RouterStub(),
                "news": RouterStub(), "sector": RouterStub(),
            }

        def get_quote(self, s):
            return self._routers["quote"].dispatch("quote", "get_quote", s)

        def get_kline(self, s, period="d", count=5):
            return self._routers["kline"].dispatch("kline", "get_kline", s)

        def get_money_flow(self, s, days=5):
            return self._routers["moneyflow"].dispatch("moneyflow", "get_money_flow", s)

        def get_margin(self, s, days=5):
            return self._routers["margin"].dispatch("margin", "get_margin", s)

        def get_lhb(self, s, days=5):
            return self._routers["lhb"].dispatch("lhb", "get_lhb", s)

        def get_financials(self, s):
            return self._routers["financials"].dispatch("financials", "get_financials", s)

        def get_news(self, s, limit=3):
            return self._routers["news"].dispatch("news", "get_news", s)

        def get_sector_snapshot(self, limit=50):
            return self._routers["sector"].dispatch("sector", "get_sector_snapshot")

        def health(self):
            return [{"provider": "p1", "domain": "quote", "state": "closed",
                     "failures": 0, "last_error": ""}]

    return Core()


def test_probe_reports_ok_and_unavailable():
    from finana.doctor import probe

    rows = {r["domain"]: r for r in probe(_stub_core(), "600519.SH")}
    assert rows["quote"]["status"] == "ok"
    assert rows["kline"]["status"] == "unavailable"
    assert rows["quote"]["ms"] >= 0
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/v2/test_doctor.py -v`
Expected: FAIL（finana.doctor 不存在）

- [ ] **Step 3: 实现**

```python
# finana/doctor.py
import argparse
import json
import time

from finana.datacore.base import DataUnavailable
from finana.observability import get_logger

log = get_logger("doctor")

PROBES = [
    ("quote", lambda c, s: c.get_quote(s)),
    ("kline", lambda c, s: c.get_kline(s, count=5)),
    ("moneyflow", lambda c, s: c.get_money_flow(s, days=5)),
    ("margin", lambda c, s: c.get_margin(s, days=5)),
    ("lhb", lambda c, s: c.get_lhb(s, days=5)),
    ("financials", lambda c, s: c.get_financials(s)),
    ("news", lambda c, s: c.get_news(s, limit=3)),
    ("sector", lambda c, s: c.get_sector_snapshot(limit=20)),
]


def probe(core, symbol: str) -> list[dict]:
    rows = []
    for domain, fn in PROBES:
        t0 = time.monotonic()
        status, detail = "ok", ""
        try:
            fn(core, symbol)
        except DataUnavailable as e:
            status, detail = "unavailable", ",".join(e.attempts)
        except Exception as e:
            status, detail = "error", f"{type(e).__name__}: {e}"
        rows.append({"domain": domain, "status": status,
                     "ms": round((time.monotonic() - t0) * 1000), "detail": detail})
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="600519")
    args = parser.parse_args()
    from finana.config import get_settings
    from finana.datacore.core import get_datacore

    core = get_datacore()
    rows = probe(core, args.symbol)
    settings = get_settings()
    settings.ensure_dirs()
    out = settings.finana_home / "doctor_last.json"
    out.write_text(json.dumps({"ts": time.time(), "rows": rows,
                               "health": core.health()},
                              ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{'domain':<12}{'status':<12}{'ms':>8}  detail")
    for r in rows:
        print(f"{r['domain']:<12}{r['status']:<12}{r['ms']:>8}  {r['detail']}")
    print("\n渠道熔断状态:")
    for h in core.health():
        print(f"{h['provider']:<16}{h['domain']:<12}{h['state']:<10} fails={h['failures']} {h['last_error']}")
    print(f"\n快照已写入 {out}")
    raise SystemExit(1 if all(r["status"] != "ok" for r in rows) else 0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试通过**

Run: `python -m pytest tests/v2/test_doctor.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add finana/doctor.py tests/v2/test_doctor.py
git commit -m "feat: add finana-doctor channel probe"
```

---

### Task 11: 渠道实测 spike——校准端点与默认优先级

**Files:**
- Modify: `finana/config.py`（新增 `provider_order: str = "..."`）、必要时 `providers/*.py` 的 URL/解析器、对应 fixture
- Test: 更新受影响 fixture 测试

**Interfaces:** 无新接口；产出的是"实测校准过的事实"。

- [ ] **Step 1: 安装可选依赖并跑真实 doctor**

```bash
pip install akshare || true
python -m finana.doctor --symbol 600519 && python -m finana.doctor --symbol 000001
```

记录每个 (provider, domain) 的 ok/error 与延迟。对 error 项：手动 curl 对应端点看原始返回，判断是 URL 变更、反爬（缺 Header/需 Cookie）、还是字段缩放差异。

- [ ] **Step 2: 修复失败渠道并刷新 fixture**

对每处修复同步更新单元测试 fixture，保证离线测试仍绿：`python -m pytest tests/v2/ -q` 全绿后才进入下一步。

- [ ] **Step 3: 按实测结果设定默认优先级**

`config.py` Settings 增加：
```python
provider_order: str = "eastmoney,sina_tencent,akshare,alltick"
```
把顺序改为实测最稳组合（例如若东财整体被反爬：`"sina_tencent,eastmoney,akshare"`），并在 `.env.example` 加注释行说明可覆盖。

- [ ] **Step 4: 全量回归 + 复跑 doctor 确认改善**

Run: `python -m pytest tests/v2/ -q && python -m finana.doctor`
Expected: 测试全绿；doctor 无 domain 级全军覆没（个别非关键域允许 unavailable 但要在提交信息中注明）

- [ ] **Step 5: Commit**

```bash
git add -A finana/ tests/v2/ .env.example
git commit -m "chore: calibrate data channels against live probes"
```

---

### Task 12: FastMCP 数据工具服务器

**Files:**
- Create: `finana/mcp_server/__init__.py`、`finana/mcp_server/server.py`
- Test: `tests/v2/test_mcp_server.py`

**Interfaces:**
- Consumes: `get_datacore()`、`DataUnavailable`
- Produces（Plan 2 的 cordis 配置将把本 server 以 stdio 方式挂给 dsh；工具名不得再改）:
  - `mcp = FastMCP("finana")`，tools：`get_realtime_quote(symbol)`、`get_kline(symbol, period, count)`、`get_money_flow(symbol, days)`、`get_margin(symbol, days)`、`get_lhb(symbol, days)`、`get_financials(symbol)`、`get_stock_news(symbol, limit)`、`get_sector_snapshot(limit)`
  - 返回紧凑 JSON 字符串；`DataUnavailable` 时返回 `"ERROR: <domain> 数据暂不可用(<渠道清单>)，请基于已有信息谨慎判断"`（模型可读的降级语义，不抛异常中断会话）
  - `build_server() -> FastMCP`（便于测试注入 mock core）；`__main__` 入口 `mcp.run()`

- [ ] **Step 1: 写失败测试**

```python
# tests/v2/test_mcp_server.py
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
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest tests/v2/test_mcp_server.py -v`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现**

```bash
touch finana/mcp_server/__init__.py
```

```python
# finana/mcp_server/server.py
import json
from dataclasses import asdict, is_dataclass

from fastmcp import FastMCP

from finana.datacore.base import DataUnavailable
from finana.observability import get_logger

log = get_logger("mcp")


def _serialize(obj):
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, list):
        return [_serialize(x) for x in obj]
    return obj


def build_server(core=None) -> FastMCP:
    mcp = FastMCP("finana")
    dc = core

    def _core():
        nonlocal dc
        if dc is None:
            from finana.datacore.core import get_datacore

            dc = get_datacore()
        return dc

    def wrap(domain):
        def deco(fn):
            def inner(*args, **kwargs):
                try:
                    return json.dumps(_serialize(fn(*args, **kwargs)), ensure_ascii=False)
                except DataUnavailable as e:
                    return f"ERROR: {domain} 数据暂不可用({','.join(e.attempts)})，请基于已有信息谨慎判断"
            inner.__name__ = fn.__name__
            inner.__doc__ = fn.__doc__
            return mcp.tool(inner)
        return deco

    @wrap("quote")
    def get_realtime_quote(symbol: str) -> dict:
        """获取A股实时行情快照(价格/涨跌幅/量额)。"""
        return _core().get_quote(symbol)

    @wrap("kline")
    def get_kline(symbol: str, period: str = "d", count: int = 120) -> list:
        """获取历史K线(前复权)。period: d/w/m。"""
        return _core().get_kline(symbol, period=period, count=count).bars

    @wrap("moneyflow")
    def get_money_flow(symbol: str, days: int = 10) -> list:
        """获取个股主力资金净流入日线序列。"""
        return _core().get_money_flow(symbol, days=days)

    @wrap("margin")
    def get_margin(symbol: str, days: int = 20) -> list:
        """获取融资融券余额明细。"""
        return _core().get_margin(symbol, days=days)

    @wrap("lhb")
    def get_lhb(symbol: str, days: int = 30) -> list:
        """获取龙虎榜上榜记录。"""
        return _core().get_lhb(symbol, days=days)

    @wrap("financials")
    def get_financials(symbol: str) -> dict:
        """获取核心财务指标(营收/净利/ROE等最新期)。"""
        return _core().get_financials(symbol)

    @wrap("news")
    def get_stock_news(symbol: str, limit: int = 10) -> list:
        """获取个股近期新闻标题列表。"""
        return _core().get_news(symbol, limit=limit)

    @wrap("sector")
    def get_sector_snapshot(limit: int = 50) -> list:
        """获取行业板块涨跌概览。"""
        return _core().get_sector_snapshot(limit=limit)

    return mcp


mcp = None


def _default():
    global mcp
    if mcp is None:
        mcp = build_server()
    return mcp


if __name__ == "__main__":
    _default().run()
```

- [ ] **Step 4: 运行测试通过 + 全量回归**

Run: `python -m pytest tests/v2/test_mcp_server.py -v && python -m pytest tests/v2/ -q`
Expected: 全部 passed

- [ ] **Step 5: 手动 stdio 冒烟（可选但建议）**

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}' | python -m finana.mcp_server.server | head -c 400
```
Expected: 输出包含 `"serverInfo"` 且含 `"finana"`（证明 stdio 通道可用）

- [ ] **Step 6: Commit**

```bash
git add finana/mcp_server/ tests/v2/test_mcp_server.py
git commit -m "feat: expose datacore as fastmcp tools"
```

---

## Plan 1 完成标准

- `python -m pytest tests/v2/ -q` 全绿
- `python -m finana.doctor` 输出健康报表且无 domain 级全灭
- MCP stdio 冒烟通过
- 所有提交均为小步提交，`git log` 干净可读

## 移交 Plan 2 的事实

- 默认渠道优先级（Task 11 实测结论，写入 config.provider_order）
- 各渠道端点实测有效性清单
- `get_datacore()` / `get_settings()` / `get_metrics()` / `get_logger()` / `run_trace` 签名不变
