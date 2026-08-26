# FinAna v2 — Plan 3: 目标规划 + 预测验证闭环 + Web 入口 + 旧版清理

> 父 Spec: docs/superpowers/specs/2026-08-25-finana-v2-deepseek-harness-design.md
> 前置: Plan 1 (DataCore, 已合 main) + Plan 2 (Harness 集成/记忆/CLI, 已合 main @ b36770e)

## 范围

闭环的最后一段：把"单次分析"升级为"可追踪、可验证、可服务"的研究系统。

1. **目标规划 (Goal)** —— L5 记忆层 + 调度器：用户提出长期目标（"跟踪茅台季度表现"），系统建立目标、拆研究任务、在 harness 空闲时触发分析/验证，并把结论回流记忆。
2. **预测验证 (Verifier)** —— 到期预测自动拉实时数据，判定方向命中/区间命中，写回 `predictions.verdict`，命中教训沉淀为语义记忆（Plan 2 schema 已留 `status`/`verdict` 列 + `due_predictions()`）。
3. **Web 入口** —— 在 `finana/api.py` 用 FastAPI 包 Orchestrator/Goals/Verifier，暴露 `/api/analyze`、`/api/goals`、`/api/verify/run`、`/api/reports`；复用现有 `reports/` 落盘。
4. **旧版清理** —— 更新 CLAUDE.md 反映 v2 架构；标记 v1 `agents/`、`workflows/`、`web_ui/`、`data/`、`llm/`、`api/`、`skills/stock_data_enhanced/` 为 legacy（不删除，避免破坏历史）；`tests/` 旧套件与 `tests/v2/` 分层说明。

## 非目标

- 不重构 v1 代码（仅标注）。
- 不引入新数据源（沿用 Plan 1 DataCore）。
- 不实现真实定时守护进程；调度器以"惰性触发"形式存在（CLI/API 调用 `process_due()` 时检查到期目标与预测），可由外部 cron 周期性调用。

## 任务拆分

### T1 — 目标规划器 (goals)
- 新建 `finana/goals.py`：
  - `Goal` dataclass: id, user_id, title, symbol, cadence_days, last_run_at, next_run_at, status(active/done/paused), created_at, notes
  - `GoalService(conn)`: create/list/get/update_status/touch/due_goals(now)/delete
  - `Planner`: `plan_from_query(query, memory) -> Goal | None` 用本地启发式从自然语言提取 {symbol, cadence}（正则 + resolve_symbol_local）；不调 LLM
  - 持久化到 `user_goals` 表（schema 追加：id TEXT PK, user_id, title, symbol, cadence_days, last_run_at REAL, next_run_at REAL, status, created_at REAL, notes TEXT）
- 测试 `tests/v2/test_goals.py`：建目标、due 计算、plan_from_query 解析"每月跟踪茅台"→ symbol=600519.SH cadence=30。

### T2 — 预测验证器 (verifier)
- 新建 `finana/verifier.py`：
  - `verify_prediction(pred_row, datacore) -> Verdict(direction_hit, range_hit, note)`：用 `DataCore.get_realtime_quote(symbol)` 取现价，对照 direction 与 target_low/high
  - `Verifier.run_due(datacore, memory, now=None) -> list[Verdict]`：遍历 `memory.due_predictions(now)`，逐个验证、写回 `predictions.verdict`/`status='verified'`、命中教训 `memory.remember_semantic(..., tags='verdict')`
  - 方向判定：up 且 price>=made_price 阈值？简化：用 target 中值或 last price。明确规则写入 docstring。
- 测试 `tests/v2/test_verifier.py`：FakeDataCore 返回固定价；单边/双边预测命中与未命中；写回 verdict。

### T3 — Web 入口 (api)
- 新建 `finana/api.py`：`FastAPI()` 应用，`POST /api/analyze {query, session_id?}` → Orchestrator.analyze；`GET/POST /api/goals`；`POST /api/verify/run` → Verifier.run_due；`GET /api/reports?symbol=` 读 reports 目录。
- 依赖 fastapi（Plan 1 requirements 已含？确认；缺则加）。uvicorn 启动入口 `finana/api.py:app`。
- 测试 `tests/v2/test_api.py`：TestClient 调用 /api/analyze 用 FakeHarness 注入；/api/goals CRUD；/api/verify/run 用 FakeDataCore。

### T4 — 旧版清理 + 文档
- 更新 `CLAUDE.md`：新增"v2 架构"段（finana 包、DeepSeek Harness、DataCore、记忆四层、预测闭环），标注 legacy 目录。
- 仓库根 `LEGACY.md`：列出 v1 模块与状态（保留原因）。
- `tests/README` 或 CLAUDE 注明：`tests/` 为 v1 历史套件（可能失效），`tests/v2/` 为 v2 现行套件。
- 不删除任何 v1 文件。

## 全局约束（同 Plan 1/2）

- Python ≥3.10；测试 `.venv/bin/python -m pytest tests/v2/<file> -v` 全绿。
- 不构造真实 DeepSeekHarness（memory/datacore 用真，harness 用 FakeHarness 注入）。
- 无代码注释；公开 API 一行 docstring；短祈使句 commit（每任务 1 个）。
- 所有 dsh 交互仍在 `harness_adapter.py`（本计划不直接触碰）。
- 数据源经 `finana.datacore.DataCore`（Plan 1 已落地）。

## 验收

- `tests/v2/` 全绿（目标/验证/API 新增）。
- `/api/analyze` 经 TestClient 跑通单次分析闭环；`/api/verify/run` 写回 verdict。
- CLAUDE.md 反映 v2；LEGACY.md 存在；v1 文件未删。
- 合并 main + 推送（用户已授权，不弹框）。

## 风险

- FastAPI 依赖未装 → T3 先确认 venv 是否含 fastapi；无则 `pip install fastapi`。
- verifier 方向判定规则需明确（现价 vs 制作时价 vs 区间）。以 docstring 固化。
- 目标调度为惰性触发，不做常驻进程（spec §6 的"调度"以 process_due 实现）。
