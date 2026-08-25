# FinAna v2 设计文档：基于 DeepSeek Harness 的自主投研 Agent

- 日期：2026-08-25
- 状态：待用户审阅
- 前置讨论：本文档为 brainstorming 阶段确认的最终设计，所有关键决策已经用户逐项确认

## 1. 背景与目标

FinAna v1 是基于 DashScope Qwen + LangGraph 固定管线的多智能体投研系统。v2 目标：**用户提出某只股票时，系统对其未来走势给出相对准确、可验证的判断**。

v1 的问题：
- 固定流水线（宏观→行业→个股→合成）不灵活，agent 无自主取数能力
- LLM 底座（DashScope Qwen）过时
- 记忆只有会话级缓存，无跨会话知识沉淀
- 数据渠道单一且不稳定

## 2. 已确认的关键决策

| 决策点 | 结论 |
|---|---|
| Agent 底座 | DeepSeek 官方开源的 **DeepSeek Harness (dsh)**，经 Python SDK 驱动，不自研循环 |
| Memory | 四层体系：会话 / 标的档案 / 语义知识 / 用户画像 |
| Goal | 单次分析任务管理 + 长期跟踪型 goal（定时回访、验证旧预测、修正结论） |
| 市场 | A 股优先；美股港股留扩展位不在本期实现 |
| 数据封装 | Python 核心库 + FastMCP 薄外壳挂给 dsh |
| 存储与入口 | 彻底重写；仅保留 CLI + 轻量 Web 两个入口；memory/goal 持久化用本地 SQLite，弃用 Redis/SeaweedFS/LangGraph/Gradio/DashScope |
| 准确性定义 | 可验证预测闭环：结构化预测 + 到期自动验证 + 命中率反馈进 memory |

## 3. 总体架构

```
┌────────────────────────── FinAna 应用进程 (Python) ──────────────────────────┐
│                                                                              │
│  CLI (REPL) ─┐                                                               │
│              ├─→ Orchestrator ──→ DeepSeekHarness (deepseek-harness-sdk)     │
│  FastAPI Web ┘   │                  │ JSON-RPC stdio                        │
│                  │                  ▼                                       │
│                  │          dsh runtime 子进程 (agent 循环/工具协议/会话日志)   │
│                  │                  │ 挂载                                   │
│                  │        ┌─────────┼──────────────┐                       │
│                  │        ▼         ▼              ▼                       │
│                  │   finana-mcp    dsh 内置       skills/                   │
│                  │   (FastMCP      (bash/web搜索/  (投研方法论 SKILL.md)     │
│                  │    stdio)       子代理/plan)                            │
│                  │                                                          │
│                  ├─→ MemoryService (SQLite: 四层记忆读写+检索注入)            │
│                  └─→ GoalScheduler (后台线程: 回访调度+预测验证)             │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 与 dsh 的集成契约

- 依赖：`deepseek-harness-sdk`（**锁定版本**，当前 0.1.1rc1）。dsh 处于 developer preview，官方明示有破坏性变更，因此：
  - 所有 dsh 交互收敛到 `finana/harness_adapter.py` 单模块（构造参数、run 调用、结果解析）
  - 升级 dsh 时只改该模块
- 核心用法：
  ```python
  from deepseek_harness import DeepSeekHarness

  with DeepSeekHarness(
      provider="deepseek-official",
      model="deepseek-v4-flash",        # 可配置
      cwd=str(workspace),
      session_root=str(sessions_dir),   # JSONL 会话持久化目录
      cordis=str(cordis_config_path),   # finana 定制组合
  ) as harness:
      result = harness.run(prompt, session_id=sid)
      # result.final_response / result.finish_reason / result.events
  ```
- 环境变量：`DEEPSEEK_API_KEY`（必需）、`DEEPSEEK_BASE_URL`（可选代理）、模型与系统提示词由配置文件管理
- 会话策略：同一用户连续追问复用 `session_id`（延续对话）；独立分析用新 id。FinAna 在 SQLite 维护 `session_id ↔ symbol/主题` 映射索引
- **cordis 组合配置**（`cordis.finana.yml`）：以仓库内 `examples/jsonrpc-agent/cordis.yml` 为基底定制——保留 jsonrpc-server 入口，挂载 MCP server（finana-mcp）、skills 目录、启用上下文压缩与 web 搜索插件、按需收紧沙箱策略。⚠️ 插件名与配置键以锁定版本实测为准，实现计划含一个校准 spike

## 4. A 股数据核心库 + MCP 外壳

### 4.1 设计原则：可插拔多渠道 + 可靠性优先

每个数据域定义统一 Provider 接口；渠道全部失败时明确降级而非报错中断。

```
finana/datacore/
├── base.py          # Provider 协议、注册表、熔断器、TTL 内存缓存、symbol 规范化
├── quote.py         # 实时行情域
├── kline.py         # 历史K线域
├── moneyflow.py     # 资金流/两融/龙虎榜域
├── financials.py    # F10 财务域
├── news.py          # 新闻公告域
├── sector.py        # 板块指数域
└── providers/       # 各渠道实现
    ├── em.py        # 东方财富直连（push2/push2his/F10/数据中心）
    ├── sina_tencent.py  # 新浪 hq.sinajs.cn + 腾讯 qt.gtimg.cn
    ├── ashare_p.py  # Ashare 库接入（新浪+腾讯双内核热备参考实现）
    ├── akshare_p.py # AKShare 接入（可选 extra，聚合器性质）
    └── alltick.py   # AllTick 免费档（可选注册，1200次/分，REST+WS）
```

候选渠道池（2026-08 调研结论）：

| 渠道 | 特点 | 风险 |
|---|---|---|
| 东财 push2/push2his/F10 | 字段最全（行情/K线/资金/F10 一站） | 反爬策略可能变化（用户曾遇不可用） |
| 新浪/腾讯 HTTP | 极简稳定，多年可用 | 字段较少 |
| Ashare 库 | 双内核自动热备切换，单文件 | 上游仍是新浪/腾讯 |
| AKShare | 覆盖面最广，社区迭代快 | 本质是上游聚合器，上游挂则挂；频率限制 |
| AllTick 免费档 | 宣称 99.9% 可用性，1200 次/分 | 免费档历史 K 线限最近 500 根；需注册 token |
| Tushare Pro | 数据治理好，稳定 | 注册积分制，免费额度有限（备选） |

- **默认优先级不写死在设计中**：实现阶段先跑渠道实测 spike（见 §9），按真实可用性排序写入配置
- **熔断降级**：连续 N 次失败 → 熔断该渠道并切下家；后台定时探测恢复
- **交叉验证**：实时价格等关键字段双源比对，偏差超阈值告警
- symbol 规范：对外接受 `600519` / `000001.SZ` / `sh600519` / 中文简称，内部统一为 `市场+代码`

### 4.2 MCP 外壳（`finana/mcp_server/server.py`）

FastMCP stdio server，工具集：

- 数据组：`get_realtime_quote` / `get_kline` / `get_money_flow` / `get_margin` / `get_lhb` / `get_financials` / `get_news` / `get_sector_snapshot`
- 记忆组：`recall_memory(query, symbol?, layers?)` / `save_analysis_memory(...)` / `get_user_profile()`

工具描述面向模型写清楚何时调用、参数含义、返回结构。数据工具返回紧凑 JSON（控制 token 占用），K 线类默认返回近 N 根 + 关键统计而非全量。

## 5. Memory 四层体系（SQLite `finana.db`）

| 层 | 存储 | 说明 |
|---|---|---|
| L1 会话 | dsh 原生 JSONL（不自建） | FinAna 仅存 session↔symbol 映射索引表 |
| L2 标的档案 | `instrument_memory` 表 | symbol 主键：名称/行业、关键结论时间线(JSON)、价格锚点、历次预测摘要、命中率统计 |
| L3 语义知识 | `semantic_memory` 表 + FTS5 全文索引 | 分析结论片段与方法论卡片，tags 过滤 + 全文检索 + 时间衰减排序；接口预留 embedding 插槽（DeepSeek 无 embedding API，本期不做向量） |
| L4 用户画像 | `user_profile` 表 | 风险偏好、关注列表、投资风格、反馈历史（单用户起步，表设计预留 user_id） |

读写路径：
- **注入**（分析前，Orchestrator 自动）：L2 档案摘要 + 该标的近期预测及命中率 + L3 相关检索 top-k + L4 画像 → 组装为 prompt 上下文块
- **深挖**（运行中）：agent 经 MCP 记忆工具自主检索/写入
- **回写**（分析后）：从结构化输出提取结论更新 L2/L3；用户显式反馈（"判断不对"）校正 L2 并记入 L4

SQLite 统一启用 WAL；启动时完整性检查。

## 6. Goal 体系（`goals` 表 + GoalScheduler 后台线程）

字段：`goal_id, type(single_analysis|tracking), symbol, status(active|paused|completed|cancelled), description, horizon, checkin_interval, next_checkin_at, checkpoints(JSON), created_at`

- **single_analysis**：创建→执行（任务内计划交给 dsh 原生 plan/todo 能力）→完成审计（报告落盘+预测入库）→关闭
- **tracking**：如"跟踪 600519 三个月"→GoalScheduler 按 interval 扫描到期 goal→发起回访 run（prompt 注入上次预测+实际走势，要求先验证旧判断再给新结论）→更新 checkpoints；状态显著变化时触发通知（CLI 提示/Web 轮询展示；邮件等推送渠道本期不做）
- 不用 dsh runtime 做常驻调度（其子进程生命周期随请求起停）

## 7. 可验证预测闭环（`predictions` 表）

字段：`prediction_id, goal_id, symbol, made_at, direction(up|down|sideways), confidence, target_low, target_high, horizon_days, invalidation_conditions, rationale_digest, status(pending|verified|expired|invalidated), verdict`

- **产出格式**：系统提示词强制要求 agent 最终回复末尾输出 ```prediction JSON``` 块（上述字段的源形式）；Orchestrator 解析失败→追加一次修正请求→仍失败标记本次无预测，不阻塞报告
- **验证 job**：预测到期（horizon_days）由 GoalScheduler 触发：取实际价格路径→判定 hit/miss/partial（方向正确性为主、目标区间为辅、失效条件触发即 invalidated）→verdict 写回，同时更新 L2 命中率统计与 L3 模式卡片（何种市况/论据类型的判断更准）
- **度量呈现**：CLI `/accuracy [symbol]`、Web `GET /api/accuracy/{symbol}` 输出总体与分标的命中率、平均置信度校准曲线（置信度 vs 实际命中）

## 8. 入口

### 8.1 CLI（`finana` 命令，交互式 REPL，rich 渲染）
- 直接自然语言提问 → 分析报告（Markdown 流式渲染 + 预测卡片高亮）
- 斜杠命令：`/track <symbol> <period>`、`/goals`、`/accuracy [symbol]`、`/profile`、`/sessions`、`/doctor`（数据源健康探测）
- 启动即检查 DEEPSEEK_API_KEY 与 SQLite 完整性

### 8.2 轻量 Web（FastAPI + 无构建单页聊天界面）
- `POST /api/chat`（SSE 流式）、`GET /api/goals`、`POST /api/goals`、`GET /api/accuracy/{symbol}`、`GET/PUT /api/profile`
- 前端为单个静态 HTML（原生 fetch+SSE），由 FastAPI 托管，无前端框架无 node 构建
- `finana web --port 8000` 启动

## 9. 错误处理与降级

| 故障 | 策略 |
|---|---|
| 单一数据渠道失败 | 熔断切换下家 |
| 某数据域全渠道失败 | 明确告知缺失域；agent 基于 L2/L3 历史记忆降级分析并在报告中标注数据陈旧时点 |
| dsh runtime 崩溃/超时 | harness_adapter 重启子进程并重试一次；会话靠 JSONL 可续 |
| prediction JSON 解析失败 | 追加一次修正请求→仍失败标记无预测 |
| API key 缺失/欠费 | 启动即校验并给出配置指引 |
| SQLite 异常 | WAL + 启动完整性检查 |

## 10. 测试策略

- **单元**：datacore providers 用录制 fixture 回放（不打真实 API）；memory/goal/prediction CRUD 与检索；熔断器状态机
- **集成**：harness_adapter 用 mock JSON-RPC 子进程测协议交互；MCP 工具用 FastMCP 内存客户端直调
- **E2E 冒烟**（需真实 key，手动/CI 可选标签）：一只股票完整分析→预测落库→模拟到期→自动验证→命中率更新
- **finana-doctor**：一键实测所有渠道当前可用性并出健康报表——既是运维工具也是渠道选型依据（渠道实测 spike 即基于它）

## 11. 代码结构与迁移

```
FinAna/
├── finana/                  # v2 包（全新）
│   ├── config.py            # pydantic-settings
│   ├── harness_adapter.py   # dsh 唯一交互模块
│   ├── orchestrator.py
│   ├── prompts/             # 系统提示词、SKILL.md、预测输出规范
│   ├── datacore/  mcp_server/  memory/  goals/  prediction/
│   ├── cli.py
│   └── web/app.py
├── cordis.finana.yml        # dsh 组合配置
├── docs/superpowers/specs/  # 本文档与后续计划
└── tests/                   # v2 测试（替换旧测试）
```

迁移决策（已确认"彻底重写"）：v1 的 `agents/ workflows/ llm/ api/ web_ui/ memory/ storage/ users/ skills/ data/ config.py cli_analyzer.py` 及旧测试在实现计划中删除（git 历史保留）。依赖收敛为：`deepseek-harness-sdk(锁版)、fastmcp、fastapi、uvicorn、rich、pydantic-settings、requests`；`akshare` 作为可选 extra。Python ≥3.10（SDK 要求）。

## 12. 风险与对策

| 风险 | 对策 |
|---|---|
| dsh developer preview 破坏性变更 | 锁版本 + harness_adapter 隔离层；升级仅改一处 |
| 免费 A 股渠道整体不稳 | 多渠道熔断 + doctor 实测选型 + AllTick/Tushare 备选注册位 |
| 预测准确率天然有限 | 闭环透明呈现命中率与置信度校准，不做虚假承诺；报告强制声明非投资建议 |
| LLM 幻觉编造数据 | 提示词强约束"只用工具返回的数据"；关键数字要求标注来源工具名 |

## 13. 本期范围外（留扩展位）

美股/港股渠道与 symbol 规范扩展；embedding 升级 L3；邮件/Webhook 推送；多用户与鉴权；组合层面（多股票对比、仓位建议）。
