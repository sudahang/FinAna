# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

FinAna v2 是个股趋势研判系统：用户问一只股票，系统拉取真实行情/财务/新闻/资金数据，交由 DeepSeek Harness 自主调研生成研判报告，并解析出**可被未来验证的趋势预测**，到期自动回测命中率，沉淀为语义教训。

v1（DashScope + LangGraph 固定管线的多智能体版本）已从仓库移除，历史保留在 git 记录中。

## 快速启动

```bash
source venv/bin/activate
export DEEPSEEK_API_KEY=sk-xxx

python -m finana.cli --once "分析600519近期走势"   # 单次分析
python -m finana.cli                                # 交互式 REPL
python -m finana.doctor --symbol 600519             # 取数渠道自检
uvicorn finana.api:web_app --reload --port 8000     # Web API + 静态页
python -m finana.cli cron                           # 处理到期目标与预测
python -m finana.mcp_server.server                  # MCP 工具服务（stdio）
```

## 测试

```bash
pytest                       # 默认跑 tests/v2（见 pytest.ini）
pytest tests/v2 -q --cov=finana
python scripts/smoke_e2e.py  # 真实 E2E，缺 key 自动 SKIP
```

## 技术栈

- **Agent 运行时**：DeepSeek Harness（`cordis.finana.yml` 组合驱动）
- **后端**：FastAPI + Pydantic / pydantic-settings
- **数据**：东方财富（主）+ 新浪/腾讯 + AKShare + Alltick，多源 failover + 聚合去重
- **存储**：SQLite + FTS5（`~/.finana/finana.db`）
- **工具暴露**：fastmcp（`mcp-finana`，stdio 供 Harness 调用）

## 项目结构

```
finana/
├── config.py             # Settings：环境变量 / .env
├── datacore/             # 取数层：core(门面) base(熔断/缓存/域路由) http models symbols providers/
├── harness_adapter.py    # 唯一隔离 DeepSeek Harness 交互的模块
├── prediction/parser.py  # 解析模型输出的 ```json 预测块
├── memory/service.py     # 四层记忆 + FTS5 + 命中率
├── orchestrator.py       # 单次分析闭环
├── goals.py              # 目标管理（建目标 / 启发式解析 / 到期扫描）
├── verifier.py           # 到期预测验证，写回 verdict，沉淀语义教训
├── scheduler.py          # GoalScheduler：到期目标回访 + 预测验证
├── mcp_server/server.py  # mcp-finana：8 数据工具 + 3 记忆工具
├── api.py                # FastAPI：/api/analyze /goals /verify/run /accuracy /profile /metrics /chat /cron /reports
├── cli.py                # REPL + --once + web + cron
├── doctor.py             # 取数渠道健康探测
├── observability.py      # 运行指标
├── prompts/              # system_prompt.md + prediction_format.md + skills/
├── web/static/           # 静态界面
└── storage/db.py         # SQLite 连接 + schema.sql

仓库根/
├── cordis.finana.yml     # Harness 组合（含 mcp-finana 段），由 harness_adapter 按仓库根解析
├── tests/v2/             # 现行 pytest 套件
└── scripts/              # install-dsh.sh（harness 运行时）、smoke_e2e.py
```

## 预测闭环

```
orchestrator 解析预测 → predictions 落库(pending) → verifier 到期拉真实价 → 写回 verdict → 命中率统计 + 语义教训
```

## 关键约束

- **所有 DeepSeek Harness 交互必须隔离在 `harness_adapter.py`**；自动化测试用 `FakeHarness` 注入，禁止在测试中构造真实 harness。
- macOS x86_64 无 runtime-bin 轮子，必须走 npm 模式（`DSH_RUNTIME=npm` + `DSH_NPM_BIN` 指向 `packaged-bin.js`）。
- 取数层新增 provider 需注册到 `datacore/registry.py`，并配 `PROVIDER_ORDER`。
- 缺 API Key 时真实 E2E 必须自动跳过，不得让 CI 失败。

## 配置（环境变量）

| 变量 | 说明 | 默认 |
|------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key（必填） | — |
| `DSH_MODEL` | Harness 模型 | `deepseek-v4-flash` |
| `DSH_RUNTIME` | `auto` / `wheel` / `npm` | `auto` |
| `DSH_NPM_BIN` | npm 模式入口（mac-x64 必填） | — |
| `FINANA_HOME` | 主目录（库/报告/日志） | `~/.finana` |
| `PROVIDER_ORDER` | 数据 provider 顺序 | `eastmoney,sina_tencent,akshare,alltick` |
| `ALLTICK_TOKEN` | Alltick 令牌（美股/港股） | — |
| `LOG_LEVEL` / `HTTP_TIMEOUT` | 日志级别 / 取数超时（秒） | `INFO` / `10` |

## 开发注意事项

- 数据层统一走 `datacore/http.py`（UA、退避重试、curl_cffi 兜底），不要各 provider 自己发请求。
- 列表型数据（新闻等）走**多源聚合去重**，单源失败不应影响整体。
- 报告与预测不构成投资建议。
