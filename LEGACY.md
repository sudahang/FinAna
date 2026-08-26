# LEGACY.md — FinAna v1 归档说明

FinAna v2 是仓库重构主线（见 CLAUDE.md 的「FinAna v2 架构」段）。以下 v1 模块保留以便历史参考与平滑迁移，但**不再主维护**，新功能请在 `finana/` 包内实现。

## v1 模块（保留，不删除）

| 路径 | 说明 | 状态 |
|------|------|------|
| `agents/` | 四智能体（宏观/行业/个股/合成器），基于 DashScope 自研循环 | 被 `finana/orchestrator.py` + DeepSeek Harness 替代 |
| `workflows/langgraph_workflow.py` | LangGraph 编排 | 被 `finana/orchestrator.py` 替代 |
| `workflows/agent_scheduler.py` | 调度 | 被 `finana/goals.py`（惰性触发）替代 |
| `data/schemas.py`, `data/finance_data.py` | v1 数据模型与抓取 | 被 `finana/datacore/` 替代 |
| `llm/client.py` | DashScope 客户端 | 被 `finana/harness_adapter.py`（DeepSeek）替代 |
| `api/` | v1 FastAPI | 被 `finana/api.py` 替代 |
| `web_ui/app.py` | Gradio UI | 待 v2 Web 替代（当前 v2 提供 FastAPI `/api/*`） |
| `skills/stock_data_enhanced/` | 股票数据 skill（多源） | 已被 `finana/datacore/` 吸收 |
| `memory/` | v1 对话记忆 | 被 `finana/memory/service.py` 四层记忆替代 |
| `storage/` | v1 Redis/SeaweedFS 缓存 | 待 v2 评估是否需要 |
| `tests/` | v1 pytest 套件 | 可能随 v1 失效；v2 现行套件在 `tests/v2/` |

## 测试分层

- `tests/v2/`：v2 现行套件，CI 以它为准。
- 根目录 `test_*.py`（如 `test_ai_agent.py`、`test_full_workflow.py`）：v1 历史集成测试，需要外部 key/服务，可能失败，不代表 v2 质量。

## 迁移建议

新需求直接扩展 `finana/`；确认 v2 覆盖某 v1 能力后，可单独 PR 删除对应 legacy 目录。
