# FinAna v2 · Plan 2：DeepSeek Harness 集成、Memory 四层与单次分析 CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Plan 1 的数据核心库接入 DeepSeek Harness 自主 agent 循环，落地 memory 四层注入/回写与预测结构化解析，交付 `finana` CLI 的单次分析闭环（自然语言 → 工具取数分析 → 报告 + 结构化预测落库）。

**Architecture:** `harness_adapter.py` 以官方 Python SDK（子进程 JSON-RPC）驱动 dsh runtime，支持 wheel/npm 双启动模式；cordis 组合挂载 finana-mcp（Plan 1）+ 投研 persona/skills + compaction；Orchestrator 在 run 前注入 memory 上下文块、run 后解析 ```prediction``` JSON 块回写 SQLite。

**Tech Stack:** deepseek-harness-sdk==0.1.1rc1（wheel 模式）/ @deepseek-ai/dsh npm 包（node 模式）、SQLite FTS5、rich。

**Spec:** docs/superpowers/specs/2026-08-25-finana-v2-deepseek-harness-design.md（§3 架构、§5 Memory、§7 预测产出格式、§8.1 CLI、§9 错误处理）
**前置事实（Plan 1 收尾时实测）：**
- 本机 macOS x86_64：runtime-bin 无对应平台轮子（仅 arm64-mac/linux），**必须走 npm/node 启动模式**；adapter 设计为双模式可切换
- 本机无 DEEPSEEK_API_KEY：所有测试离线（Fake harness / mock 子进程），真实 E2E 冒烟做成 key-gated 脚本
- SDK rc 版本需显式 pin；npm 树大安装慢，spike 任务负责完成安装并钉死启动命令

## Global Constraints

- 延续 Plan 1 约束：Python ≥3.10；测试在 tests/v2/ 用 `.venv/bin/python -m pytest tests/v2/<file> -v`（主仓库 venv 已装 fastmcp/requests-mock/pydantic-settings/deepseek-harness-sdk）；SQLite WAL + schema.sql 幂等追加；代码不加注释、公共 API 一行 docstring；短祈使句提交
- 所有 dsh 交互只允许出现在 finana/harness_adapter.py（隔离 preview 变更）
- 工具名冻结（Plan 1 T12）；prediction JSON 字段名冻结（本计划 Task 4 定义，Plan 3 verifier 消费）
- 不打真实 LLM API 于任何自动化测试；live 冒烟仅限 key 存在时的手动脚本
- memory 注入块必须控制长度（上限常量），防 token 失控

---

### Task 1: 配置扩展与依赖锁定

**Files:**
- Modify: `finana/config.py`
- Modify: `requirements.txt`
- Test: `tests/v2/test_config.py`（追加用例）

**Interfaces:**
- Produces: Settings 新字段 `deepseek_base_url`(已有)、`dsh_model`(已有)、`dsh_max_tokens: int = 49152`、`dsh_runtime: str = "auto"`(auto|wheel|npm)、`dsh_npm_bin: str = ""`（node 模式下 jsonrpc 入口 js 绝对路径，spike 后可写入 .env）、`report_ttl_days: int = 30`

- [ ] **Step 1: 写失败测试**（tests/v2/test_config.py 追加）

```python
def test_dsh_settings_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("FINANA_HOME", str(tmp_path))
    from finana.config import Settings

    s = Settings()
    assert s.dsh_runtime == "auto"
    assert s.dsh_max_tokens == 49152
    assert s.report_ttl_days == 30


def test_dsh_npm_bin_override(monkeypatch, tmp_path):
    monkeypatch.setenv("FINANA_HOME", str(tmp_path))
    monkeypatch.setenv("DSH_NPM_BIN", "/opt/dsh/jsonrpc-agent.mjs")
    from finana.config import Settings

    assert str(Settings().dsh_npm_bin) == "/opt/dsh/jsonrpc-agent.mjs"
```

- [ ] **Step 2: 运行确认失败**：`.venv/bin/python -m pytest tests/v2/test_config.py -v` → 新增 2 用例 FAIL

- [ ] **Step 3: 实现**：Settings 追加字段 `dsh_max_tokens: int = 49152`、`dsh_runtime: str = "auto"`、`dsh_npm_bin: Path | None = None`、`report_ttl_days: int = 30`；`.env.example` 追加注释行说明 DSH_RUNTIME=auto|wheel|npm 与 DSH_NPM_BIN 用法；requirements.txt 在 deepseek-harness-sdk 行写 `deepseek-harness-sdk==0.1.1rc1  # 需 --pre；runtime-bin 无 mac-x64 轮子时走 npm 模式(DSH_RUNTIME=npm)`

- [ ] **Step 4: 测试通过 + 全量回归**

- [ ] **Step 5: Commit** `feat: add harness settings and sdk pin`

### Task 2: prediction 解析器

**Files:**
- Create: `finana/prediction/parser.py`
- Test: `tests/v2/test_prediction_parser.py`

**Interfaces:**
- Produces:
  - `PredictionDraft` dataclass: `direction(str)|confidence(float)|target_low(float|None)|target_high(float|None)|horizon_days(int)|invalidation(list[str])|rationale(str)`
  - `parse_prediction(text: str) -> PredictionDraft | None`：提取最后一个 ```json ... ``` 固定围栏块（或首个以 `{` 开头且含 `"direction"` 的平衡对象），校验 direction ∈ {up,down,sideways}、confidence∈[0,1]、horizon_days 正整数；非法/缺失返回 None；多余字段忽略
- Consumes: 无

（代码块同 Plan 1 风格完整给出：正则 r"```(?:json)?\s*(\{.*?\})\s*```" DOTALL 取最后一组 + json.loads + 字段校验 + 手工平衡括号兜底扫描）

- Steps: 失败测试（合法/无块/坏direction/越界confidence/非整数horizon/尾随文本多块取最后）→ 实现 → 通过 → `feat: add prediction block parser`

### Task 3: memory schema 与 MemoryService

**Files:**
- Modify: `finana/storage/schema.sql`（追加 4 表 + FTS5 虚表）
- Create: `finana/memory/service.py`
- Test: `tests/v2/test_memory_service.py`

**Schema 追加：**
```sql
CREATE TABLE IF NOT EXISTS session_index (
  session_id TEXT PRIMARY KEY,
  symbol TEXT,
  topic TEXT,
  updated_at REAL NOT NULL DEFAULT (strftime('%s','now'))
);
CREATE TABLE IF NOT EXISTS instrument_memory (
  symbol TEXT PRIMARY KEY,
  name TEXT DEFAULT '',
  sector TEXT DEFAULT '',
  conclusions_json TEXT NOT NULL DEFAULT '[]',
  price_anchors_json TEXT NOT NULL DEFAULT '[]',
  hit_total INTEGER NOT NULL DEFAULT 0,
  hit_ok INTEGER NOT NULL DEFAULT 0,
  updated_at REAL NOT NULL DEFAULT (strftime('%s','now'))
);
CREATE TABLE IF NOT EXISTS semantic_memory (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  content TEXT NOT NULL,
  tags TEXT NOT NULL DEFAULT '',
  source_trace TEXT DEFAULT '',
  created_at REAL NOT NULL DEFAULT (strftime('%s','now'))
);
CREATE VIRTUAL TABLE IF NOT EXISTS semantic_fts USING fts5(content, tags, content='semantic_memory', content_rowid='id');
CREATE TRIGGER IF NOT EXISTS semantic_ai AFTER INSERT ON semantic_memory BEGIN
  INSERT INTO semantic_fts(rowid,content,tags) VALUES (new.id,new.content,new.tags);
END;
CREATE TABLE IF NOT EXISTS user_profile (
  user_id TEXT PRIMARY KEY DEFAULT 'default',
  risk_preference TEXT DEFAULT '',
  style TEXT DEFAULT '',
  watchlist_json TEXT NOT NULL DEFAULT '[]',
  feedback_json TEXT NOT NULL DEFAULT '[]',
  updated_at REAL NOT NULL DEFAULT (strftime('%s','now'))
);
CREATE TABLE IF NOT EXISTS predictions (
  prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
  trace_id TEXT,
  symbol TEXT NOT NULL,
  made_at REAL NOT NULL,
  direction TEXT NOT NULL,
  confidence REAL NOT NULL,
  target_low REAL,
  target_high REAL,
  horizon_days INTEGER NOT NULL,
  invalidation_json TEXT NOT NULL DEFAULT '[]',
  rationale TEXT DEFAULT '',
  status TEXT NOT NULL DEFAULT 'pending',
  verdict TEXT DEFAULT ''
);
```

**MemoryService 接口（全部经显式 conn 构造）：**
- `upsert_instrument(symbol,name,sector,conclusion)`；`get_instrument(symbol) -> dict|None`（conclusions 反序列化，附命中率 hit_ok/hit_total）
- `remember_semantic(content,tags,trace)`；`search_semantic(query,k=5) -> list[dict]`（FTS5 MATCH，空查询回退最近 k 条）
- `get_profile() -> dict`（缺省 default 行自建）；`update_profile(**fields)`
- `bind_session(session_id,symbol)`；`symbol_for_session(session_id) -> str|None`
- `save_prediction(d: PredictionDraft, symbol, trace_id) -> int`；`due_predictions(now) -> list[dict]`（status='pending' AND made_at+horizon_days*86400<=now）
- `build_context_block(symbol,user_query) -> str`：L2 摘要（≤400字）+ 该标的 pending 预测摘要 + L3 top-k（每条≤120字，总≤600字）+ L4 画像一行——各段缺失跳过，整体 ≤1200 字符，空库返回 ""

Steps: schema 追加后 connect() 自动生效（幂等）→ service 失败测试（instrument upsert/get 往返、FTS 中文检索、profile 默认行、save/due_predictions 时间窗、context_block 各段裁剪与空库路径）→ 实现 → 全绿 → `feat: add memory layers service with fts5`

### Task 4: harness_adapter

**Files:**
- Create: `finana/harness_adapter.py`
- Test: `tests/v2/test_harness_adapter.py`

**Interfaces:**
- `AnalysisOutcome` dataclass: `final_response:str|None, finish_reason:str|None, usage:dict, session_id:str`
- `HarnessAdapter`: 
  - `__init__(settings=None)`；惰性构建底层 driver
  - `run(prompt, session_id) -> AnalysisOutcome`：内部 try 一次，`finish_reason in ("error", None)` 或底层异常时重启 driver 重试一次，再失败抛 `HarnessUnavailable`
  - `close()`
  - 私有 `_build_driver()`：按 settings.dsh_runtime 分派——"wheel": import deepseek_harness.DeepSeekHarness(provider="deepseek-official", model=settings.dsh_model, max_tokens=settings.dsh_max_tokens, cwd=str(workspace), session_root=str(settings.sessions_dir), cordis=str(cordis_path))；"npm": 同上但传 runtime_bin=生成的 wrapper 脚本路径（wrapper 内容 `#!/bin/sh\nexec node <settings.dsh_npm_bin> "$@"`，写入 settings.finana_home/"bin"，chmod+x）；"auto": wheel 可导入且 runtime-bin 可用则 wheel 否则 npm
  - workspace = settings.finana_home/"workspace"
- `FakeHarness`（导出供测试）：构造时接收预设 AnalysisOutcome 列表，记录 calls
- usage 提取：从 RunResult.events 中找 assistant/message 事件聚合 inputTokens/outputTokens（容错缺失→{}）

测试全部基于 FakeHarness + monkeypatch _build_driver：成功直通、error→重启→成功、两次失败抛 HarnessUnavailable、npm wrapper 文件生成与内容断言（tmp home）。

Commit: `feat: add harness adapter with restart retry`

### Task 5: prompts 与 skill 资产

**Files:**
- Create: `finana/prompts/system_prompt.md`、`finana/prompts/prediction_format.md`、`finana/prompts/skills/stock-research/SKILL.md`、`finana/prompts/loader.py`
- Test: `tests/v2/test_prompts.py`

system_prompt.md 要点（中文，≤60 行）：投研分析师角色；**只用工具返回的数据**、关键数字标注来源工具；数据缺失时明示并降级基于记忆；输出末尾必须含 prediction JSON 块（引用 prediction_format.md 全文拼接）；免责声明一行。
prediction_format.md：字段表 direction/confidence/target_low/target_high/horizon_days/invalidation/rationale + 一个完整示例 + “无法给出预测时省略整个块”。
SKILL.md：A股研究流程方法论（行情→趋势位置→资金/两融→基本面→新闻催化→综合判断；何时调哪个 MCP 工具；交叉验证要求）。
loader.py: `load_system_prompt(include_prediction_format=True) -> str`、`load_skill(name) -> str`（importlib.resources 或 Path(__file__) 定位）。
测试：loader 返回非空且包含关键锚点字符串（如 "prediction"、"龙虎榜"）；文件存在性。
Commit: `feat: add research prompts and skill assets`

### Task 6: Orchestrator

**Files:**
- Create: `finana/orchestrator.py`
- Test: `tests/v2/test_orchestrator.py`

**Interfaces:**
- `AnalysisResult` dataclass: `response_md:str, prediction:PredictionDraft|None, prediction_id:int|None, trace_id:str, session_id:str, from_memory_only:bool`
- `Orchestrator(memory=None, adapter=None, metrics=None)`（默认真实组件，测试注入 Fake）
- `analyze(query, session_id=None) -> AnalysisResult` 流程：
  1. trace = run_trace()
  2. symbol 解析：优先 adapter 不可知——本地启发 `resolve_symbol_local(query)`：正则抓 6 位数字/带后缀码 → normalize_symbol；否则查 instrument_memory 名称 LIKE；仍无则 symbol=None
  3. ctx_block = memory.build_context_block(symbol,…)
  4. prompt = f"{ctx_block}\n\n用户问题: {query}"（前缀系统提示由 cordis persona 承担，不在此重复）
  5. outcome = adapter.run(prompt, session_id or 新 uuid)
  6. pred = parse_prediction(outcome.final_response)；pred 且 symbol → memory.save_prediction + 更新 instrument conclusions（截取 response 前200字为 conclusion 条目 append）
  7. memory.bind_session(session_id, symbol)
  8. 报告落盘 reports/{ts}-{symbol|general}.md；metrics.record("analysis.latency_ms",…,stage="total")
  9. DataUnavailable 场景已在 MCP 层降级为 ERROR 文本，orchestrator 不特殊处理；HarnessUnavailable 向上抛（CLI/Web 捕获展示）
- 测试（FakeHarness 预设响应含合法/缺失 prediction 块；内存 sqlite）：全链路断言 prediction 落库、session 绑定、报告文件生成、from_memory_only=False；无 symbol 时跳过落库仍出结果。
Commit: `feat: add analysis orchestrator with memory writeback`

### Task 7: cordis 组合配置 + spike 校准

**Files:**
- Create: `cordis.finana.yml`、`scripts/install-dsh.sh`
- Modify: 无代码
- Test: `tests/v2/test_cordis_config.py`（yaml 可解析、必含锚点键：sdk-jsonrpc-server/llm-deepseek/agent-spine(persona 引用)/sessions(root 指向 env)/compaction-basic/mcp 客户端段含 "finana"）

cordis.finana.yml 以官方示例全文为基底修改：
- agent-spine.persona: `!!js "process.env.DSH_SYSTEM_PROMPT ?? ''"`（adapter 经 env 注入 loader 产物）
- skills.enabled: true + catalog 指向 finana/prompts/skills（确切键名 spike 定）
- sessions.root: `process.env.DSH_SESSION_ROOT ?? './.sessions'`（沿用 env 注入）
- 新增 mcp-client 段挂载 stdio server：command `.venv/bin/python -m finana.mcp_server.server`，cwd=仓库根（**插件 id/config 键由 spike 实测确定**）
- bash timeoutMs 提到 120000；保留 compaction/checkpoints/token-meter/subagent/todo

**Spike 步骤（Task 内执行并写报告 docs/superpowers/notes/dsh-spike.md）：**
1. 完成 @deepseek-ai/dsh@0.1.1-rc.2 npm 安装（npmmirror 镜像可用）；定位 bin 入口（package.json bin 字段）与 JSON-RPC 启动参数（--help / examples/jsonrpc-agent 说明）
2. 在已装包内 grep dsh-mcp-client 的 README/types 得 config 键名（servers? command/args/env?）
3. 用 `DSH_SYSTEM_PROMPT=ping node <bin> <jsonrpc参数>` + 手工 JSON-RPC initialize 探活（无需 API key 即可完成握手层验证）
4. 将确定的启动命令写入 .env.example 注释与 Settings.dsh_npm_bin 默认值留空由用户填
Commit(s): `feat: add finana cordis composition` + `chore: calibrate dsh launch via npm spike`

### Task 8: CLI 单次分析 REPL

**Files:**
- Create: `finana/cli.py`、`finana/__main__.py`
- Test: `tests/v2/test_cli.py`

行为：`python -m finana` 进入 REPL（rich console）：
- 输入即问题 → orchestrator.analyze → Markdown 渲染 final_response；prediction 存在时渲染预测卡片表（方向/置信度/区间/horizon）
- 斜杠：`/quit` `/help` `/new`（新 session uuid）`/session`（显示当前 id 与绑定 symbol）`/profile set risk=保守`（k=v 解析写 profile）
- HarnessUnavailable → 打印友好错误 + 本次 trace_id；Ctrl+C 退出
- `--once "问题"` 非交互模式（Web/脚本复用）
测试：Capsys + 注入 Fake orchestrator 工厂（cli.main(argv, factory=…) 依赖注入避免真 adapter）；断言 once 模式输出含响应文本与预测卡片字段；/profile set 落库。
Commit: `feat: add interactive cli for single analysis`

### Task 9: live 冒烟脚本（key-gated）

**Files:**
- Create: `scripts/smoke_e2e.py`
- Test: 无自动化（脚本本身打印 SKIP/OK）

逻辑：读 Settings；缺 DEEPSEEK_API_KEY → print SKIP + exit 0；否则 orchestrator.analyze("贵州茅台近期走势如何？") 断言 final_response 非空且 parse_prediction 或明确无预测；打印耗时与 token。文档注明运行前提（key + npm dsh 安装完成 + doctor 全 ok）。
Commit: `feat: add gated e2e smoke script`

## Plan 2 完成标准

- 全量 tests/v2 绿（预计 ≥95 用例）
- spike 报告存在且 .env.example 含可执行的启动命令模板
- key 缺失时 smoke_e2e 打印 SKIP；CLI once 模式在 Fake 下端到端可用
- 移交 Plan 3：predictions 表结构、MemoryService 接口、AnalysisResult、trace_id 贯径

## 移交 Plan 3 的消费契约

- `memory.service.MemoryService.due_predictions(now)` → verifier 输入
- predictions.verdict 写回 + instrument hit_* 计数更新接口（Plan 3 补 `record_verdict()`）
- GoalScheduler 线程复用 observability.run_trace 与 MetricsService
